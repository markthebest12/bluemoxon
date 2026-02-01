import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

import {
  CognitoIdentityProviderClient,
  InitiateAuthCommand,
} from "@aws-sdk/client-cognito-identity-provider";
import { GetSecretValueCommand, SecretsManagerClient } from "@aws-sdk/client-secrets-manager";
import type { FullConfig } from "@playwright/test";

const REGION = "us-west-2";

const ENV_DEFAULTS = {
  staging: { clientId: "4bb77j6uskmjibq27i15ajfpqq", secretPrefix: "bluemoxon-staging" },
  production: { clientId: "3ndaok3psd2ncqfjrdb57825he", secretPrefix: "bluemoxon-prod" },
} as const;

function resolveEnvConfig(baseURL: string) {
  const isProd =
    baseURL === "https://app.bluemoxon.com" || baseURL === "https://api.bluemoxon.com";
  const defaults = isProd ? ENV_DEFAULTS.production : ENV_DEFAULTS.staging;
  return {
    clientId: process.env.COGNITO_CLIENT_ID || defaults.clientId,
    secretPrefix: process.env.E2E_SECRET_PREFIX || defaults.secretPrefix,
  };
}

interface TestUser {
  email: string;
  secretName: string;
  storageFile: string;
}

function getTestUsers(secretPrefix: string): TestUser[] {
  return [
    {
      email: "e2e-test-admin@bluemoxon.com",
      secretName: `${secretPrefix}/e2e-admin-password`,
      storageFile: "admin.json",
    },
    {
      email: "e2e-test-editor@bluemoxon.com",
      secretName: `${secretPrefix}/e2e-editor-password`,
      storageFile: "editor.json",
    },
    {
      email: "e2e-test-viewer@bluemoxon.com",
      secretName: `${secretPrefix}/e2e-viewer-password`,
      storageFile: "viewer.json",
    },
  ];
}

function decodeJwtPayload(token: string): Record<string, unknown> {
  const parts = token.split(".");
  if (parts.length !== 3) {
    throw new Error("Invalid JWT token format");
  }
  const payload = parts[1];
  const decoded = Buffer.from(payload, "base64url").toString("utf-8");
  return JSON.parse(decoded);
}

async function getSecretValue(client: SecretsManagerClient, secretName: string): Promise<string> {
  const command = new GetSecretValueCommand({ SecretId: secretName });
  const response = await client.send(command);
  if (!response.SecretString) {
    throw new Error(`Secret ${secretName} has no string value`);
  }
  return response.SecretString;
}

async function authenticateUser(
  cognitoClient: CognitoIdentityProviderClient,
  secretsClient: SecretsManagerClient,
  user: TestUser,
  authDir: string,
  baseURL: string,
  clientId: string
): Promise<void> {
  const password = await getSecretValue(secretsClient, user.secretName);

  const command = new InitiateAuthCommand({
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: clientId,
    AuthParameters: {
      USERNAME: user.email,
      PASSWORD: password,
    },
  });

  const response = await cognitoClient.send(command);
  const result = response.AuthenticationResult;

  if (!result?.IdToken || !result.AccessToken || !result.RefreshToken) {
    throw new Error(`Authentication failed for ${user.email}: missing tokens in response`);
  }

  const payload = decodeJwtPayload(result.IdToken);
  const sub = payload.sub as string;

  if (!sub) {
    throw new Error(`Could not extract sub from IdToken for ${user.email}`);
  }

  const prefix = `CognitoIdentityServiceProvider.${clientId}`;

  const storageState = {
    cookies: [],
    origins: [
      {
        origin: baseURL,
        localStorage: [
          {
            name: `${prefix}.${sub}.idToken`,
            value: result.IdToken,
          },
          {
            name: `${prefix}.${sub}.accessToken`,
            value: result.AccessToken,
          },
          {
            name: `${prefix}.${sub}.refreshToken`,
            value: result.RefreshToken,
          },
          {
            name: `${prefix}.${sub}.clockDrift`,
            value: "0",
          },
          {
            name: `${prefix}.LastAuthUser`,
            value: sub,
          },
        ],
      },
    ],
  };

  const filePath = join(authDir, user.storageFile);
  await writeFile(filePath, JSON.stringify(storageState, null, 2));
  console.log(`Authenticated ${user.email} -> ${filePath}`);
}

async function writeEmptyAuthState(
  authDir: string,
  baseURL: string,
  testUsers: TestUser[]
): Promise<void> {
  const emptyState = { cookies: [], origins: [{ origin: baseURL, localStorage: [] }] };
  await Promise.all(
    testUsers.map((user) => {
      const filePath = join(authDir, user.storageFile);
      return writeFile(filePath, JSON.stringify(emptyState, null, 2));
    })
  );
}

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use?.baseURL || "https://staging.app.bluemoxon.com";
  const { clientId, secretPrefix } = resolveEnvConfig(baseURL);
  const testUsers = getTestUsers(secretPrefix);

  console.log(`E2E env: ${baseURL.includes("staging") || baseURL.includes("localhost") ? "staging" : "production"} (prefix=${secretPrefix})`);

  const authDir = join(process.cwd(), ".auth");
  await mkdir(authDir, { recursive: true });

  // Skip AWS auth setup when SKIP_AUTH_SETUP is set (local dev without AWS credentials)
  if (process.env.SKIP_AUTH_SETUP === "true" || process.env.SKIP_AUTH_SETUP === "1") {
    if (process.env.CI) {
      throw new Error("SKIP_AUTH_SETUP must not be set in CI — it disables all auth testing");
    }
    console.warn("WARNING: SKIP_AUTH_SETUP is set. Auth state files will be empty.");
    console.warn("WARNING: Tests requiring authentication WILL FAIL. This is for local dev only.");
    await writeEmptyAuthState(authDir, baseURL, testUsers);
    return;
  }

  const cognitoClient = new CognitoIdentityProviderClient({
    region: REGION,
  });
  const secretsClient = new SecretsManagerClient({ region: REGION });

  const results = await Promise.allSettled(
    testUsers.map((user) =>
      authenticateUser(cognitoClient, secretsClient, user, authDir, baseURL, clientId)
    )
  );

  const failures: string[] = [];
  const successes: string[] = [];
  results.forEach((result, index) => {
    const email = testUsers[index].email;
    if (result.status === "fulfilled") {
      successes.push(email);
    } else {
      failures.push(`${email}: ${result.reason}`);
    }
  });

  if (successes.length > 0) {
    console.log(`Authenticated successfully: ${successes.join(", ")}`);
  }

  if (failures.length > 0) {
    console.error(`Authentication failures:\n${failures.join("\n")}`);
    throw new Error(
      `Global setup failed: ${failures.length}/${results.length} users failed authentication`
    );
  }

  console.log("Global setup complete: all test users authenticated");
}

export default globalSetup;

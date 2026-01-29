import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

import {
  CognitoIdentityProviderClient,
  InitiateAuthCommand,
} from "@aws-sdk/client-cognito-identity-provider";
import {
  GetSecretValueCommand,
  SecretsManagerClient,
} from "@aws-sdk/client-secrets-manager";
import type { FullConfig } from "@playwright/test";

const REGION = "us-west-2";
const CLIENT_ID = "4bb77j6uskmjibq27i15ajfpqq";

interface TestUser {
  email: string;
  secretName: string;
  storageFile: string;
}

const TEST_USERS: TestUser[] = [
  {
    email: "e2e-test-admin@bluemoxon.com",
    secretName: "bluemoxon-staging/e2e-admin-password",
    storageFile: "admin.json",
  },
  {
    email: "e2e-test-editor@bluemoxon.com",
    secretName: "bluemoxon-staging/e2e-editor-password",
    storageFile: "editor.json",
  },
  {
    email: "e2e-test-viewer@bluemoxon.com",
    secretName: "bluemoxon-staging/e2e-viewer-password",
    storageFile: "viewer.json",
  },
];

function decodeJwtPayload(token: string): Record<string, unknown> {
  const parts = token.split(".");
  if (parts.length !== 3) {
    throw new Error("Invalid JWT token format");
  }
  const payload = parts[1];
  const decoded = Buffer.from(payload, "base64url").toString("utf-8");
  return JSON.parse(decoded);
}

async function getSecretValue(
  client: SecretsManagerClient,
  secretName: string,
): Promise<string> {
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
): Promise<void> {
  const password = await getSecretValue(secretsClient, user.secretName);

  const command = new InitiateAuthCommand({
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: CLIENT_ID,
    AuthParameters: {
      USERNAME: user.email,
      PASSWORD: password,
    },
  });

  const response = await cognitoClient.send(command);
  const result = response.AuthenticationResult;

  if (!result?.IdToken || !result.AccessToken || !result.RefreshToken) {
    throw new Error(
      `Authentication failed for ${user.email}: missing tokens in response`,
    );
  }

  const payload = decodeJwtPayload(result.IdToken);
  const sub = payload.sub as string;

  if (!sub) {
    throw new Error(
      `Could not extract sub from IdToken for ${user.email}`,
    );
  }

  const prefix = `CognitoIdentityServiceProvider.${CLIENT_ID}`;

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

async function globalSetup(config: FullConfig) {
  const baseURL =
    config.projects[0]?.use?.baseURL ||
    "https://staging.app.bluemoxon.com";

  const authDir = join(process.cwd(), ".auth");
  await mkdir(authDir, { recursive: true });

  const cognitoClient = new CognitoIdentityProviderClient({
    region: REGION,
  });
  const secretsClient = new SecretsManagerClient({ region: REGION });

  await Promise.all(
    TEST_USERS.map((user) =>
      authenticateUser(
        cognitoClient,
        secretsClient,
        user,
        authDir,
        baseURL,
      ),
    ),
  );

  console.log("Global setup complete: all test users authenticated");
}

export default globalSetup;

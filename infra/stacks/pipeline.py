"""Pipeline Stack - CodePipeline CI/CD."""

from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cpactions,
    aws_codebuild as codebuild,
    aws_iam as iam,
)
from constructs import Construct


class PipelineStack(Stack):
    """Creates CodePipeline for CI/CD."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Source artifact
        source_output = codepipeline.Artifact("SourceOutput")

        # Build artifacts
        frontend_build_output = codepipeline.Artifact("FrontendBuildOutput")
        backend_build_output = codepipeline.Artifact("BackendBuildOutput")

        # CodeBuild project for frontend
        frontend_build = codebuild.PipelineProject(
            self,
            "FrontendBuild",
            project_name="bluemoxon-frontend-build",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {"nodejs": "18"},
                        "commands": ["cd frontend", "npm ci"],
                    },
                    "build": {
                        "commands": [
                            "npm run lint",
                            "npm run type-check",
                            "npm run test -- --run",
                            "npm run build",
                        ],
                    },
                },
                "artifacts": {
                    "base-directory": "frontend/dist",
                    "files": ["**/*"],
                },
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
            ),
        )

        # CodeBuild project for backend
        backend_build = codebuild.PipelineProject(
            self,
            "BackendBuild",
            project_name="bluemoxon-backend-build",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {"python": "3.11"},
                        "commands": [
                            "cd backend",
                            "pip install poetry",
                            "poetry install",
                        ],
                    },
                    "build": {
                        "commands": [
                            "poetry run black --check .",
                            "poetry run ruff check .",
                            "poetry run pytest",
                        ],
                    },
                },
                "artifacts": {
                    "base-directory": "backend",
                    "files": ["**/*"],
                },
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
            ),
        )

        # CodeBuild project for deployment
        deploy_project = codebuild.PipelineProject(
            self,
            "DeployProject",
            project_name="bluemoxon-deploy",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {"python": "3.11", "nodejs": "18"},
                        "commands": [
                            "npm install -g aws-cdk",
                            "cd infra",
                            "pip install poetry",
                            "poetry install",
                        ],
                    },
                    "build": {
                        "commands": [
                            "cdk deploy --all --require-approval never",
                        ],
                    },
                },
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True,
            ),
        )

        # Grant deploy project admin access (for CDK)
        deploy_project.add_to_role_policy(
            iam.PolicyStatement(
                actions=["*"],
                resources=["*"],
            )
        )

        # Pipeline
        self.pipeline = codepipeline.Pipeline(
            self,
            "BlueMoxonPipeline",
            pipeline_name="bluemoxon-pipeline",
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        cpactions.GitHubSourceAction(
                            action_name="GitHub",
                            owner="OWNER",  # Replace with your GitHub username
                            repo="bluemoxon",
                            branch="main",
                            oauth_token=None,  # Use GitHub connection instead
                            output=source_output,
                            trigger=cpactions.GitHubTrigger.WEBHOOK,
                        ),
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[
                        cpactions.CodeBuildAction(
                            action_name="BuildFrontend",
                            project=frontend_build,
                            input=source_output,
                            outputs=[frontend_build_output],
                            run_order=1,
                        ),
                        cpactions.CodeBuildAction(
                            action_name="BuildBackend",
                            project=backend_build,
                            input=source_output,
                            outputs=[backend_build_output],
                            run_order=1,
                        ),
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="Approval",
                    actions=[
                        cpactions.ManualApprovalAction(
                            action_name="Approve",
                            run_order=1,
                        ),
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="Deploy",
                    actions=[
                        cpactions.CodeBuildAction(
                            action_name="Deploy",
                            project=deploy_project,
                            input=source_output,
                            run_order=1,
                        ),
                    ],
                ),
            ],
        )

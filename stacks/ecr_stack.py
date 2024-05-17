"""Provision Amazon ECR repo and build container image"""
from constructs import Construct
from aws_cdk.aws_ecr_assets import DockerImageAsset, Platform    
from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
    aws_iam as iam,
    aws_kms as kms,
    aws_ecr as ecr,
    aws_eks as eks,
    custom_resources as cr,
    RemovalPolicy,
)

class EcrStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, cluster, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # creating an container image from asset, which locally builds the image and tags/pushes it into an asset ecr repo
        
        app_container = DockerImageAsset(self, "MyBuildImage",
            directory="docker",
            platform=Platform.LINUX_AMD64
        )
        
        # use asset.imageUri to reference the image. which includes both the ECR image URL and tag for later substitution into manifest.
        self.container_tag=app_container.image_uri # Reference for a downstream Stack
        
        cfn_access_entry = eks.CfnAccessEntry(self, "MyCfnAccessEntry",
            cluster_name="genai-cluster",
            principal_arn="arn:aws:iam::851725325557:role/aws-reserved/sso.amazonaws.com/eu-west-1/AWSReservedSSO_SuperAdminAccess_a2ec05493bd5b79b",
            access_policies=[eks.CfnAccessEntry.AccessPolicyProperty(
                access_scope=eks.CfnAccessEntry.AccessScopeProperty(
                    type="cluster",
                ),
                policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
            )],
            kubernetes_groups=[],
            type="STANDARD",
        )
        
        cfn_access_entry.node.add_dependency(app_container)
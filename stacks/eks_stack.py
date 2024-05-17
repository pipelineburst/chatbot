"""Provision Amazon EKS cluster for image verification with Kyverno"""
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_kms as kms,
    aws_eks as eks,
    aws_iam as iam,
    RemovalPolicy,
    lambda_layer_kubectl_v29,
    custom_resources as cr,
)

class EksStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ### 1. Prep work prior to creating the EKS cluster
        # Defining an IAM role for eks-admin

        admin_role = iam.Role(self, "eks-admin",
            role_name="aws-eks-admin",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal(service="eks.amazonaws.com"),
                iam.AnyPrincipal(),  # without it, SSO users can't assume the role
            ),
        )
        admin_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
        )

        # Defining cluster logging options

        k8s_logging_params=[
            eks.ClusterLoggingTypes.API,
            eks.ClusterLoggingTypes.AUTHENTICATOR,
            eks.ClusterLoggingTypes.AUDIT,
            eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
            eks.ClusterLoggingTypes.SCHEDULER,
        ]
 
        # Defining a KMS key object for secret encryption
        
        eks_key = kms.Key(self, "eksSecreteEncryptionKey",
            enable_key_rotation=True,
            alias="eksSecreteEncryptionKey",
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        ### 2. Creating the EKS cluster
        # Creating the EKS cluster     
        
        cluster = eks.Cluster(self, "EKS genai cluster",
            cluster_name="genai-cluster",
            version=eks.KubernetesVersion.V1_29,
            masters_role=admin_role, # this adds the eks-admin role to aws-auth as systems:masters
            default_capacity=0,
            cluster_logging=k8s_logging_params,
            vpc=vpc, # passed in from the vpc stack 
            kubectl_layer=lambda_layer_kubectl_v29.KubectlV29Layer(
                self, "kubectl"
                ),
            secrets_encryption_key=eks_key,
        )
        
        self.ekscluster=cluster # Reference for a downstream Stack

        # Adding a managed node group with ec2 worker nodes to the cluster 

        admin_role.grant_assume_role(cluster.admin_role) # grant permission to admin_role to assume the cluster admin_role

        # Defining an EC2 instance role with EKS and Bedrock permissions
        instance_role = iam.Role(self, "InstanceRole",
                                 assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                                 managed_policies=[
                                     iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSWorkerNodePolicy"),
                                     iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKS_CNI_Policy"),
                                     iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"),
                                     iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
                                 ]
                                 )
        
        instance_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel"
                ],
                resources=["arn:aws:bedrock:{}::foundation-model/anthropic.claude-v2".format(self.region)]
            )
        )

        # Adding a managed node group for the worker node tier 

        cluster.add_nodegroup_capacity("custom-node-group",
            instance_types=[ec2.InstanceType("t3a.xlarge")],
            min_size=1,
            disk_size=100,
            ami_type=eks.NodegroupAmiType.BOTTLEROCKET_X86_64,
            node_role=instance_role,
            taints=[eks.TaintSpec(key="node.cilium.io/agent-not-ready", value="true", effect=eks.TaintEffect.NO_EXECUTE)],
        )

        ### 3. Post cluster creation actions
        # Adding our readonly role to aws-auth config map (legacy)
        
        # cluster.aws_auth.add_role_mapping(
        #     readonly_role, groups=["system:authenticated"]
        # )
        
        # for existing clusters: change authenticationMode and enable access entry via custom resource
    
        onUpdateClusterAuthModeParams = {
            "name": str(cluster.cluster_name), # "name" is mandatory and is case sensitive, which is part of the http api post but not part of the body json of the api call. also see boto3 https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/eks/client/update_cluster_config.html
            "accessConfig": { 
                "authenticationMode": "API_AND_CONFIG_MAP"
            },
        }

        auth_cr = cr.AwsCustomResource(self, "AuthModeEnabler",
                on_create=cr.AwsSdkCall(
                    service="EKS",
                    action="UpdateClusterConfig",
                    parameters=onUpdateClusterAuthModeParams,
                    physical_resource_id=cr.PhysicalResourceId.of("Parameter.ARN")), # useage of pysical resource id remains unclear to me but mandatory
                policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                    resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
                    )
            )

        auth_cr.node.add_dependency(cluster)
        
        auth_cr.get_response_field("update.status")
         
        # # add cloudformation statement to create eks access entry

        # cfn_access_entry_admin = eks.CfnAccessEntry(self, "MyCfnAccessEntryAdmin",
        #     cluster_name=cluster.cluster_name,
        #     principal_arn=admin_role.role_arn,
        #     access_policies=[eks.CfnAccessEntry.AccessPolicyProperty(
        #         access_scope=eks.CfnAccessEntry.AccessScopeProperty(
        #             type="cluster",
        #         ),
        #         policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
        #     )],
        #     kubernetes_groups=[],
        #     type="STANDARD",
        # )

        # cfn_access_entry_admin.node.add_dependency(auth_cr)

        # # add cloudformation statement to create eks access entry for SSO users

        # cfn_access_entry = eks.CfnAccessEntry(self, "MyCfnAccessEntry",
        #     cluster_name=cluster.cluster_name,
        #     principal_arn="arn:aws:iam::851725325557:role/aws-reserved/sso.amazonaws.com/eu-west-1/AWSReservedSSO_SuperAdminAccess_a2ec05493bd5b79b",
        #     access_policies=[eks.CfnAccessEntry.AccessPolicyProperty(
        #         access_scope=eks.CfnAccessEntry.AccessScopeProperty(
        #             type="cluster",
        #         ),
        #         policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
        #     )],
        #     kubernetes_groups=[],
        #     type="STANDARD",
        # )

        # cfn_access_entry.node.add_dependency(auth_cr)
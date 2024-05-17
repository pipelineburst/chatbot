"""Provision a custom VPC for Amazon EKS"""
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    Tags,
)

class VpcStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ### Creating a custom VPC to configure to our preferences
        # Defining the VPC
        
        vpc = ec2.Vpc(self, "vpc-eks",
            vpc_name="vpc-eks",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="EksPrivate",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=19,
                ),
                ec2.SubnetConfiguration(
                    name="EksPublic",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=27,
                ),
                ec2.SubnetConfiguration(
                    name="EksOther",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=28,
                ),
            ],
        )
        # Adding VPC Flowlogs with defaults
        vpc.add_flow_log("eksVpcFlowlogs",
            )

        # Adding NACL rules

        default_nacl = ec2.NetworkAcl.from_network_acl_id(
            self, "DefaultNACL", vpc.vpc_default_network_acl
        )
        
        default_nacl.add_entry(
            "Block_ssh",
            cidr=ec2.AclCidr.any_ipv4(),
            direction=ec2.TrafficDirection.INGRESS,
            rule_action=ec2.Action.DENY,
            rule_number=99,
            traffic=ec2.AclTraffic.tcp_port(22),
            )
        default_nacl.add_entry(
            "Block_Rdp",
            cidr=ec2.AclCidr.any_ipv4(),
            direction=ec2.TrafficDirection.INGRESS,
            rule_action=ec2.Action.DENY,
            rule_number=98,
            traffic=ec2.AclTraffic.tcp_port(3389),
        )

        # Adding an S3 EndPoint GW
        s3_ep = ec2.GatewayVpcEndpoint(
            self,
            "VpcS3Ep",
            vpc=vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )
        Tags.of(s3_ep).add(
            key="Name",
            value="s3-ep",
            include_resource_types=["AWS::EC2::VPCEndpoint"],
        )

        # Adding an ECR EndPoint
        ecr_ep = ec2.InterfaceVpcEndpoint(
            self,
            "EcrEp",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
        )
        Tags.of(ecr_ep).add(
            key="Name",
            value="ecr-ep",
            include_resource_types=["AWS::EC2::VPCEndpoint"],
        )

        # Adding a CloudWatch EndPoint
        cw_ep = ec2.InterfaceVpcEndpoint(
            self,
            "CwEp",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH,
        )
        Tags.of(cw_ep).add(
            key="Name",
            value="cloudwatch-ep",
            include_resource_types=["AWS::EC2::VPCEndpoint"],
        )

        self.eksvpc=vpc # Reference for a downstream Stack
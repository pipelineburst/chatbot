#!/usr/bin/env python3

import aws_cdk as cdk
from stacks.ecr_stack import EcrStack
from stacks.vpc_stack import VpcStack
from stacks.eks_stack import EksStack
from stacks.chart_stack import WorkloadDeploy
import os

app = cdk.App()

### example ref app

account_id = "851725325557"
region = "eu-central-1"

stack1 = VpcStack(app, "VpcStack",
            description="Provision custom VPC resources for GenAI Bedrock App", 
            termination_protection=False, 
            tags={"project":"genai"}, 
            env=cdk.Environment(region=region, account=account_id),
        )

stack2 = EksStack(app, "EksStack", 
            description="Provision EKS cluster resources for GenAI Bedrock App", 
            termination_protection=False, 
            tags={"project":"genai"}, 
            env=cdk.Environment(region=region, account=account_id),
            vpc=stack1.eksvpc,
        )

stack3 = EcrStack(app, "EcrStack", 
            description="Provision ECR resources for GenAI Bedrock App", 
            termination_protection=False, 
            tags={"project":"genai"}, 
            env=cdk.Environment(region=region, account=account_id),
            cluster=stack2.ekscluster,            
        )

stack4 = WorkloadDeploy(app, "WorkloadDeployStack",
            description="Deploy Streamlit App", 
            termination_protection=False, 
            tags={"project":"genai"}, 
            env=cdk.Environment(region=region, account=account_id),
            cluster=stack2.ekscluster,
            container=stack3.container_tag
        )

stack2.add_dependency(stack1)
stack3.add_dependency(stack2)
stack4.add_dependency(stack3)

cdk.Tags.of(stack1).add(key="owner",value="validation")
cdk.Tags.of(stack2).add(key="owner",value="validation")
cdk.Tags.of(stack3).add(key="owner",value="validation")

app.synth()

"""Deploy helm chart and other workloads onto EKS cluster"""
import yaml
from constructs import Construct, Dependable
from aws_cdk import (
    Stack,
    aws_eks as eks,
    aws_signer as signer,
    aws_iam as iam,
    custom_resources as cr,
)

class WorkloadDeploy(Stack):

    def __init__(self, scope: Construct, construct_id: str, cluster, container, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # replace __image__ with another string
        with open('assets/streamlit.yaml') as f:
                data = f.read()
                data = data.replace('__IMAGE__', str(container))
                
        cluster.add_manifest('deployment',
                             yaml.safe_load(data)
                             )

        # adding charts with add_helm_chart; works, but we cannot set a dependency
        cluster.add_helm_chart("cilium",
                            chart="cilium",
                            repository="https://helm.cilium.io/",
                            release="cilium",
                            namespace="kube-system",
                            version="1.15.1",
                            values={
                                "eni": {
                                    "enabled": "true",
                                },
                                "ipam": {
                                    "mode": "eni",
                                },
                                "egressMasqueradeInterfaces": "eth0",
                                "operator": {
                                    "replicas": 1,
                                },
                                "routingMode": "native",
                                "encryption": {
                                    "type": "wireguard",
                                    "enabled": "true",
                                    "nodeEncryption": "true",
                                },
                            },
                            )

        ### works, but we cannot set a dependency
        cluster.add_helm_chart("tetragon",
                            chart="tetragon",
                            repository="https://helm.cilium.io/",
                            release="tetragon",
                            namespace="kube-system",
                            version="1.0.2",
                            )

        # eks.HelmChart(self, "fluxOciChart",
        #     cluster=cluster,
        #     chart="helm-controller",
        #     repository="oci://public.ecr.aws/l0g8r8j6/fluxcd",
        #     create_namespace=True,
        #     namespace="oci",
        # )

        # cluster.add_helm_chart("flux",
        #     chart="sourceController",
        #     repository="oci://ghcr.io/fluxcd-community/charts/flux2",
        #     release="flux",
        #     # values={
        #     #     "git.url":"git@github.com\:pipelineburst/gitops"
        #     # },
        #     create_namespace=True,
        #     namespace="flux-system",
        # )
        
        # # cluster.add_helm_chart("kyverno-policies",
        #     chart="kyverno-policies",
        #     repository="https://kyverno.github.io/kyverno/",
        #     release="kyverno-policies",
        #     version="3.0.4",
        #     create_namespace=False,
        #     namespace="kyverno",
        # )
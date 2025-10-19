from importlib import resources

from hyperscale.ozone import cfn_nag
from troposphere import awslambda
from troposphere import efs
from troposphere import GetAtt
from troposphere import iam
from troposphere import logs
from troposphere import Output
from troposphere import Parameter
from troposphere import Ref
from troposphere import Sub
from troposphere import Template


def _load_handler_code() -> str:
    return resources.files("efs_restore").joinpath("efs_restore_lambda.py").read_text()


class EfsRestore:
    def create_template(self) -> Template:
        template = Template()
        template.set_description("EFS Restore")
        self.add_resources(template)
        return template

    def add_resources(self, template: Template) -> None:
        file_system_id_param = template.add_parameter(
            Parameter(
                "FileSystemId",
                Type="String",
                Description="EFS filesystem ID to mount",
            )
        )
        security_group_id_param = template.add_parameter(
            Parameter(
                "SecurityGroupId",
                Type="String",
                Description=(
                    "Security group already configured for NFS access (port 2049)"
                ),
            )
        )
        subnet_id_param = template.add_parameter(
            Parameter(
                "SubnetId",
                Type="String",
                Description="Subnet for Lambda deployment",
            )
        )
        restore_directory_pattern_param = template.add_parameter(
            Parameter(
                "RestoreDirectoryPattern",
                Type="String",
                Description="Directory name pattern for restore directories",
                Default="aws-backup-restore_*",
            )
        )
        access_point = template.add_resource(
            efs.AccessPoint(
                "EfsRestoreAccessPoint",
                FileSystemId=Ref(file_system_id_param),
                RootDirectory=efs.RootDirectory(
                    Path="/",
                ),
                PosixUser=efs.PosixUser(
                    Uid="0",
                    Gid="0",
                ),
            )
        )
        efs_restore_role = template.add_resource(
            iam.Role(
                "EfsRestoreRole",
                AssumeRolePolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": "sts:AssumeRole",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                        }
                    ],
                },
                ManagedPolicyArns=[
                    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                ],
                Policies=[
                    iam.Policy(
                        PolicyName="VpcAccessPolicy",
                        PolicyDocument={
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": [
                                        "ec2:CreateNetworkInterface",
                                        "ec2:DeleteNetworkInterface",
                                        "ec2:DescribeNetworkInterfaces",
                                        "ec2:DetachNetworkInterface",
                                    ],
                                    "Resource": "*",
                                },
                            ],
                        },
                    )
                ],
            )
        )
        log_group = template.add_resource(
            logs.LogGroup(
                "EfsRestoreLogGroup",
                DeletionPolicy="Delete",
                UpdateReplacePolicy="Delete",
                Metadata=cfn_nag.suppress(
                    [cfn_nag.rule(id="W84", reason="No sensitive data logged")]
                ),
                LogGroupName=Sub("/${AWS::StackName}/efs-restore"),
                RetentionInDays="3",
            )
        )
        code = _load_handler_code()
        func = template.add_resource(
            awslambda.Function(
                "EfsRestoreLambdaFunction",
                Runtime="python3.13",
                Code=awslambda.Code(ZipFile=code.strip()),
                Handler="index.handle",
                Role=GetAtt(efs_restore_role, "Arn"),
                Timeout=900,
                MemorySize=1024,
                ReservedConcurrentExecutions=1,
                Architectures=["arm64"],
                LoggingConfig=awslambda.LoggingConfig(
                    LogGroup=Ref(log_group),
                    LogFormat="JSON",
                    ApplicationLogLevel="INFO",
                    SystemLogLevel="INFO",
                ),
                VpcConfig=awslambda.VPCConfig(
                    SecurityGroupIds=[Ref(security_group_id_param)],
                    SubnetIds=[Ref(subnet_id_param)],
                ),
                FileSystemConfigs=[
                    awslambda.FileSystemConfig(
                        Arn=GetAtt(access_point, "Arn"),
                        LocalMountPath="/mnt/efs",
                    )
                ],
                Environment=awslambda.Environment(
                    Variables={
                        "RESTORE_DIRECTORY_PATTERN": Ref(
                            restore_directory_pattern_param
                        ),
                    }
                ),
            )
        )
        template.add_output(
            Output(
                "LambdaFunctionName",
                Value=Ref(func),
                Description="Lambda function name for use with aws lambda invoke",
            )
        )
        template.add_output(
            Output(
                "LambdaFunctionArn",
                Value=GetAtt(func, "Arn"),
                Description="Full ARN of the Lambda function",
            )
        )


if __name__ == "__main__":
    template = EfsRestore().create_template()
    print(template.to_json())

import boto3

file_system_id = "fs-xxx"
security_group_id = "sg-xxx"
subnet_id = "subnet-xxx"

cfn = boto3.client("cloudformation")

cfn.create_stack(
    StackName="efs-restore-stack",
    TemplateBody=open("template.yaml").read(),
    Parameters=[
        {"ParameterKey": "FileSystemId", "ParameterValue": file_system_id},
        {"ParameterKey": "SecurityGroupId", "ParameterValue": security_group_id},
        {"ParameterKey": "SubnetId", "ParameterValue": subnet_id},
    ],
    Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
)

waiter = cfn.get_waiter("stack_create_complete")
waiter.wait(StackName="efs-restore-stack")


def get_lambda_function_name():
    for output in cfn.describe_stacks(StackName="efs-restore-stack")["Stacks"][0][
        "Outputs"
    ]:
        if output["OutputKey"] == "LambdaFunctionName":
            return output["OutputValue"]
    raise Exception("LambdaFunctionName not found")


fn = get_lambda_function_name()
lambda_ = boto3.client("lambda")
response = lambda_.invoke(FunctionName=fn)
print(response)

cfn.delete_stack(StackName="efs-restore-stack")

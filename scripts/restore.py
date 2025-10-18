import boto3
import subprocess

version = subprocess.run(['uv', 'version', '--short'], capture_output=True, text=True).stdout.strip()
file_system_id = 'fs-03b1b10c40225cfeb'
security_group_id = 'sg-0369146fcc8608416'
subnet_id = 'subnet-032ae7044859b635b'

cfn = boto3.client('cloudformation')

cfn.create_stack(
    StackName='efs-restore-stack',
    TemplateBody=open('template.yaml').read(),
    Parameters=[
        {
            'ParameterKey': 'FileSystemId',
            'ParameterValue': file_system_id
        },
        {
            'ParameterKey': 'SecurityGroupId',
            'ParameterValue': security_group_id
        },
        {
            'ParameterKey': 'SubnetId',
            'ParameterValue': subnet_id
        }
    ],
    Capabilities=['CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND'],
)

waiter = cfn.get_waiter('stack_create_complete')
waiter.wait(StackName='efs-restore-stack')


def get_lambda_function_name():
    for output in cfn.describe_stacks(StackName='efs-restore-stack')['Stacks'][0]['Outputs']:
        if output['OutputKey'] == 'LambdaFunctionName':
            return output['OutputValue']
    raise Exception('LambdaFunctionName not found')


fn = get_lambda_function_name()
lambda_ = boto3.client('lambda')
response = lambda_.invoke(FunctionName=fn)
print(response)

#cfn.delete_stack(StackName='efs-restore-stack')

import os
from azure.storage.blob import BlobServiceClient


def connect_to_storage_with_connstr():
    try:
        # the envs are from the secret reference defined in pod.yaml. And the secret is created by Service Connector
        # when creating the connection between the AKS cluster and the Azure OpenAI service
        client_connstr = BlobServiceClient.from_connection_string(
            conn_str=os.environ.get("AZURE_STORAGEBLOB_CONNECTIONSTRING")
        )
        containers = client_connstr.list_containers()
        print("Connect to Azure Storage succeeded. Find {} containers".format(len(list(containers))))
    except Exception as e:
        print("Connect to Azure Storage failed: {}".format(e))


if __name__ == "__main__":
    connect_to_storage_with_connstr()
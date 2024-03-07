# A sample code to test the connection between an AKS cluster and an Azure OpenAI service
# The connection is established by Service Connector, and the connection string is stored in AKS secret

import json
import os
from openai import AzureOpenAI
from azure.identity import (
    DefaultAzureCredential, 
    get_bearer_token_provider
)


# Send request to OpenAI service to test the connection
def test_connection_to_openai(client):
     # send request to OpenAI
    content = "Hello, OpenAI!"
    completion = client.chat.completions.create(
        # please make sure the model deployment exists in your Azure OpenAI service
        model="<MyModel>",
        messages=[
            {
                "role": "user",
                "content": content,
            },
        ],
    )
    print("Greatings to OpenAI: {}".format(content))

    # get response from OpenAI
    res = json.loads(completion.model_dump_json(indent=2))
    reply = res.get('choices', [dict()])[0].get('message', dict()).get('content')[:100] + '...'
    print("Reply from OpenAI: {}".format(reply))

    # check if the connection is successful
    if reply:
        print("Connect to Azure OpenAI service succeeded.")
    else:
        print("Connect to Azure OpenAI service failed.")


# Connect to OpenAI service using workload identity
def connect_to_openai_with_identity():
    # https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning
    api_version = "2023-07-01-preview"

    # create an Azure OpenAI client
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAI(
        api_version=api_version,
        # the envs are from the secret reference defined in pod.yaml. And the secret is created by Service Connector
        # when creating the connection between the AKS cluster and the Azure OpenAI service
        azure_endpoint=os.environ.get("AZURE_OPENAI_BASE"),
        azure_ad_token_provider=token_provider,
    )

    test_connection_to_openai(client)


if __name__ == "__main__":
    connect_to_openai_with_identity()

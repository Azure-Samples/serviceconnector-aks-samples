---
title: 'Tutorial: Connect to Azure storage account in Azure Kubernetes Service (AKS) with Service Connector using workload identity'
description: Learn how to connect to an Azure storage account using workload identity with the help of Service Connector
author: houk-ms
ms.author: honc
ms.service: service-connector
ms.custom: devx-track-python
ms.topic: tutorial
ms.date: 03/01/2024
---
Learn how to create a pod in an AKS cluster, which talks to an Azure storage account using workload identity with the help of Service Connector. In this tutorial, you complete the following tasks:

> [!div class="checklist"]
>
> * Create an AKS cluster and an Azure storage account.
> * Create a connection between the AKS cluster and the Azure storage account with Service Connector.
> * Clone a sample application that will talk to the Azure storage account from an AKS cluster.
> * Deploy the application to a pod in AKS cluster and test the connection.
> * Clean up resources.

## Prerequisites

* An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/).
* [Install](/cli/azure/install-azure-cli) the Azure CLI, and sign in to Azure CLI by using the [az login](/cli/azure/reference-index#az-login) command.
* Install [Docker ](https://docs.docker.com/get-docker/)and [kubectl](https://kubernetes.io/docs/tasks/tools/), to manage container image and Kubernetes resources.
* A basic understanding of container and AKS. Get started from [preparing an application for AKS](../aks/tutorial-kubernetes-prepare-app.md).
* A basic understanding of [workload identity](/entra/workload-id/workload-identities-overview).

## Create Azure resources

1. Create a resource group for this tutorial.

```azurecli
az group create \
    --name MyResourceGroup \
    --location eastus
```

2. Create an AKS cluster with the following command, or referring to the [tutorial](../aks/learn/quick-kubernetes-deploy-cli.md). We create the service connection, pod definition and deploy the sample application to this cluster.

```azurecli
az aks create \
    --resource-group MyResourceGroup \
    --name MyAKSCluster \
    --enable-managed-identity \
    --node-count 1
```

And connect to the cluster with the following command.

```azurecli
az aks get-credentials \
    --resource-group MyResourceGroup \
    --name MyAKSCluster
```

3. Create an Azure storage account with the following command, or referring to the [tutorial](../storage/common/storage-account-create.md). This is the target service that is connected to the AKS cluster and sample application interacts with.

```azurecli
az storage account create \
    --resource-group MyResourceGroup \
    --name MyStorageAccount \
    --location eastus \
    --sku Standard_LRS
```

4. Create an Azure container registry with the following command, or referring to the [tutorial](../container-registry/container-registry-get-started-portal.md). The registry hosts the container image of the sample application, which will be consumed by the AKS pod definition.

```azurecli
az acr create \
    --resource-group MyResourceGroup \
    --name MyRegistry \
    --sku Standard
```

And enable anonymous pull so that AKS cluster can consume the images in the registry.

```azurecli
az acr update \
    --resource-group MyResourceGroup \
    --name MyRegistry \
    --anonymous-pull-enabled
```

5. Create a user-assigned managed identity with the following command, or referring to the [tutorial](/entra/identity/managed-identities-azure-resources/how-manage-user-assigned-managed-identities). The user-assigned managed identity is used in service connection creation to enable workload identity for AKS workloads.

```azurecli
az identity create \
    --resource-group MyResourceGroup \
    --name MyIdentity
```

## Create service connection with Service Connector

#### Using Azure portal

Create a service connection between an AKS cluster and an Azure storage account with Azure portal, you may get started with Azure portal from the [quickstart](quickstart-portal-aks-connection.md). Fill in the settings with choices in the following tables, and leave other settings with their default values.

**Basics tab**

| Setting                   | Choice                 | Description                                                                               |
| ------------------------- | ---------------------- | ----------------------------------------------------------------------------------------- |
| **Service type**    | *Storage - Blob*     | The target service type.                                                                  |
| **Subscription**    | `<MySubscription>`   | The subscription for your target service (Azure Blob Storage).                            |
| **Connection name** | *storage_conn*       | Use the connection name provided by Service Connector or choose your own connection name. |
| **Storage account** | `<MyStorageAccount>` | The target storage account you want to connect to.                                       |
| **Client type**     | *Python*             | The code language or framework you use to connect to the target service.                  |

**Authentication tab**

| Authentication Setting         | Choice                | Description                                                               |
| ------------------------------ | --------------------- | ------------------------------------------------------------------------- |
| **Authentication type**  | *Workload Identity* | Service Connector authentication type.                                    |
| User assigned managed identity | `<MyIdentity>`      | A user assigned managed identity is needed to enable workload identity. |

View the kubernetes resources created by Service Connector after the connection creation succeeds.

:::image type="content" source="./media/aks-tutorial/kubernetes-resources.png" alt-text="Screenshot of the Azure portal, viewing kubernetes resources created by Service Connector.":::

#### Using Azure CLI

Use the Azure CLI command to create a service connection to the Azure storage account, providing the following information:

- **Source compute service resource group name:** the resource group name of the AKS cluster.
- **AKS cluster name:** the name of your AKS cluster that connects to the target service.
- **Target service resource group name:** the resource group name of the Azure storage account.
- **Storage account name:** the Azure storage account that is connected.
- **User-assigned identity subscription id:** the subscription ID of the user-assigned identity used to create workload identity.
- **User-assigned identity client id:** the client ID of the user-assigned identity used to create workload identity.

```azurecli
az aks connection create storage-blob \
    --user-identity client-id=<MyIdentity-ClientId> subs-id=<MyIdentity-SubscriptionId>
```

## Clone sample application

1. Clone the sample repository:

   ```Bash
   git clone https://github.com/Azure-Samples/serviceconnector-aks-samples.git
   ```
2. Go to the repository's sample folder for Azure storage:

   ```Bash
   cd serviceconnector-aks-samples/azure-storage-workload-identity
   ```

## Build and push container image

1. Build and push the images to your container registry using the Azure CLI [`az acr build`](https://learn.microsoft.com/en-us/cli/azure/acr#az_acr_build) command.

```azurecli
az acr build --registry <MyRegistry> --image sc-demo-storage-identity:latest ./
```

2. View the images in your container registry using the [`az acr repository list`](https://learn.microsoft.com/en-us/cli/azure/acr/repository#az_acr_repository_list) command.

```azurecli
az acr repository list --name <MyRegistry> --output table
```

## Run application and test connection

1. Replace the placeholders in the `pod.yaml` file in the `azure-storage-identity` folder.

   * Replace `<YourContainerImage>` with the image name we build in last step, for example, `<MyRegistry>.azurecr.io/sc-demo-storage-identity:latest`.
   * Replace `<ServiceAccountCreatedByServiceConnector>` with the service account created by Service Connector after the connection creation. You may check the service account name in the Azure portal of Service Connector.
   * Replace `<SecretCreatedByServiceConnector>` with the secret created by Service Connector after the connection creation. You may check the secret name in the Azure portal of Service Connector.
2. Deploy the pod to your cluster with `kubectl apply` command. Install `kubectl` locally using the [az aks install-cli](/cli/azure/aks#az_aks_install_cli) command if it isn't installed. The command creates a pod named `sc-demo-storage-identity` in the default namespace of your AKS cluster.

   ```Bash
   kubectl apply -f pod.yaml
   ```
3. Check the deployment is successful by viewing the pod with `kubectl`.

   ```Bash
   kubectl get pod/sc-demo-storage-identity
   ```
4. Check connection is established by viewing the logs with `kubectl`.

   ```Bash
   kubectl logs pod/sc-demo-storage-identity
   ```

## Clean up resources

Clean up the Azure resources in this tutorial by deleting the resource group.

```azurecli
az group delete \
    --resource-group MyResourceGroup
```

## Next steps

Read the following articles to learn more about Service Connector concepts and how it helps AKS connect to services.

> [!div class="nextstepaction"]
> [Learn about Service Connector concepts](./concept-service-connector-internals.md)

> [!div class="nextstepaction"]
> [Use Service Connector to connect an AKS cluster to other cloud services](./how-to-use-service-connector-in-aks.md)

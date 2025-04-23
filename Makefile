PROJECT_ID = etherlink-infra-dev-6204
REGION = europe-west2
REPOSITORY = glass
IMAGE_NAME = glass
SERVICE_NAME = glass-service
JOB_NAME = glass-service
TAG = latest
ARCH = amd64

GCP_REGISTRY = ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}

.PHONY: help setup-enable-apis create-repo setup build-amd64 build-arm push-amd64 push-arm deploy

help:
	@echo "Usage:"
	@echo "  make setup-enable-apis    Enable required GCP APIs"
	@echo "  make create-repo          Create GCP Artifact Registry repository"
	@echo "  make setup                One-time setup (APIs + repository)"
	@echo "  make build-amd64          Build AMD64 image"
	@echo "  make build-arm            Build ARM64 image"
	@echo "  make push-amd64           Push AMD64 image to GCP"
	@echo "  make push-arm             Push ARM64 image to GCP"
	@echo "  make deploy               Deploy to Cloud Run Job"
	@echo "  make deploy-amd64         Full AMD64 deployment"
	@echo "  make deploy-arm           Full ARM64 deployment"

setup-enable-apis:
	gcloud services enable \
		artifactregistry.googleapis.com \
		run.googleapis.com \
		--project=${PROJECT_ID}

create-repo:
	gcloud artifacts repositories create ${REPOSITORY} \
		--repository-format=docker \
		--location=${REGION} \
		--description="Docker repository for Glass service" \
		--project=${PROJECT_ID}

setup: setup-enable-apis create-repo

build-amd64:
	docker build --platform linux/amd64 -t ${GCP_REGISTRY}:${TAG}-amd64 .

build-arm:
	docker build --platform linux/arm64 -t ${GCP_REGISTRY}:${TAG}-arm64 .

push-amd64:
	docker push ${GCP_REGISTRY}:${TAG}-amd64

push-arm:
	docker push ${GCP_REGISTRY}:${TAG}-arm64

deploy:
	@echo "Deploying Cloud Run Job..."
	gcloud beta run jobs deploy ${JOB_NAME} \
		--image ${GCP_REGISTRY}:${TAG}-${ARCH} \
		--region ${REGION} \
		--project=${PROJECT_ID} \
		--execution-environment=gen2 \
		--cpu=1

deploy-amd64: build-amd64 push-amd64 deploy

deploy-arm: build-arm push-arm deploy
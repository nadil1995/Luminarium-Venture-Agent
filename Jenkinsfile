pipeline {
    agent any

    environment {
        DOCKER_IMAGE   = "nadil95/luminarium-agent:latest"
        EC2_HOST       = "54.151.85.104"
        EC2_USER       = "ubuntu"
        SSH_CREDENTIALS = "geo-ssh"
        APP_DIR        = "/home/ubuntu/startupAgent"
    }

    stages {

        stage('Checkout Code') {
            steps {
                git branch: 'main', url: 'https://github.com/nadil1995/Luminarium-Venture-Agent.git'
            }
        }

        stage('Build & Push Docker Image') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "Logging in to Docker Hub..."
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        echo "Building Docker image..."
                        export DOCKER_BUILDKIT=0
                        docker build -t $DOCKER_IMAGE .

                        echo "Pushing image to Docker Hub..."
                        docker push $DOCKER_IMAGE

                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent([SSH_CREDENTIALS]) {
                    sh '''
                        echo "Copying compose files to EC2..."
                        ssh -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST "mkdir -p $APP_DIR"

                        scp -o StrictHostKeyChecking=no docker-compose.yml $EC2_USER@$EC2_HOST:$APP_DIR/docker-compose.yml
                        scp -o StrictHostKeyChecking=no .env.example        $EC2_USER@$EC2_HOST:$APP_DIR/.env.example

                        echo "Deploying containers on EC2..."
                        ssh -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST "
                            cd $APP_DIR

                            echo 'Stopping old containers...'
                            sudo docker stop luminarium_agent luminarium_web 2>/dev/null || true
                            sudo docker rm   luminarium_agent luminarium_web 2>/dev/null || true

                            echo 'Pulling latest image...'
                            sudo docker pull $DOCKER_IMAGE

                            echo 'Starting containers with docker compose...'
                            sudo docker compose up -d

                            echo 'Running containers:'
                            sudo docker compose ps
                        "
                    '''
                }
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    sleep 10
                    curl --retry 5 --retry-delay 3 --silent --fail \
                        http://$EC2_HOST:5050/ > /dev/null \
                        && echo "Web UI is up at http://$EC2_HOST:5050" \
                        || echo "Warning: web UI not reachable — check EC2 security group port 5050"
                '''
            }
        }
    }

    post {
        success {
            echo "Deployment completed successfully! App: http://${EC2_HOST}:5050"
        }
        failure {
            echo "Pipeline failed! Check the logs above."
        }
        always {
            cleanWs()
        }
    }
}

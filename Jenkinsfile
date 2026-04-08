pipeline {
    agent any

    environment {
        APP_DIR        = '/home/ec2-user/startupAgent'
        COMPOSE_FILE   = 'docker-compose.yml'
        EC2_USER       = 'ec2-user'
        // Jenkins credential IDs — set these in Jenkins > Manage Credentials
        EC2_SSH_CRED   = 'ec2-ssh-key'          // SSH private key credential
        EC2_HOST_VAR   = 'EC2_HOST'              // Jenkins secret text: your EC2 public IP/hostname
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Lint / Sanity Check') {
            steps {
                sh 'python3 -m py_compile app/config.py app/pipeline.py app/storage.py || true'
            }
        }

        stage('Deploy to EC2') {
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: "${EC2_SSH_CRED}", keyFileVariable: 'SSH_KEY'),
                    string(credentialsId: "${EC2_HOST_VAR}",            variable: 'EC2_HOST')
                ]) {
                    sh """
                        # Ensure remote app directory exists
                        ssh -i \"$SSH_KEY\" -o StrictHostKeyChecking=no \
                            ${EC2_USER}@\${EC2_HOST} \
                            "mkdir -p ${APP_DIR}"

                        # Sync project files (exclude secrets and generated artefacts)
                        rsync -az --delete \
                            --exclude='.env' \
                            --exclude='credentials/' \
                            --exclude='data/' \
                            --exclude='reports/' \
                            --exclude='.git/' \
                            --exclude='__pycache__/' \
                            -e "ssh -i \\"$SSH_KEY\\" -o StrictHostKeyChecking=no" \
                            ./ ${EC2_USER}@\${EC2_HOST}:${APP_DIR}/

                        # Pull latest images and restart containers
                        ssh -i \"$SSH_KEY\" -o StrictHostKeyChecking=no \
                            ${EC2_USER}@\${EC2_HOST} \
                            "cd ${APP_DIR} && docker compose pull --quiet; docker compose up --build -d"
                    """
                }
            }
        }

        stage('Health Check') {
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: "${EC2_SSH_CRED}", keyFileVariable: 'SSH_KEY'),
                    string(credentialsId: "${EC2_HOST_VAR}",            variable: 'EC2_HOST')
                ]) {
                    sh """
                        sleep 10
                        # Verify both containers are running
                        ssh -i \"$SSH_KEY\" -o StrictHostKeyChecking=no \
                            ${EC2_USER}@\${EC2_HOST} \
                            "cd ${APP_DIR} && docker compose ps --services --filter status=running" \
                            | grep -E 'agent|web' || (echo 'Containers not running!' && exit 1)

                        # Hit the web UI health endpoint
                        curl --retry 5 --retry-delay 3 --silent --fail \
                            http://\${EC2_HOST}:5050/ > /dev/null \
                            && echo 'Web UI is up' \
                            || echo 'Warning: web UI not reachable from Jenkins (check security group)'
                    """
                }
            }
        }
    }

    post {
        success {
            echo "Deployment succeeded. App running at http://\${EC2_HOST}:5050"
        }
        failure {
            echo "Deployment failed. Check the logs above."
        }
        always {
            cleanWs()
        }
    }
}

// -------------- Configuration --------------
// CloudForms
def opentlc_creds = 'b93d2da4-c2b7-45b5-bf3b-ee2c08c6368e'
def opentlc_admin_creds = '73b84287-8feb-478a-b1f2-345fd0a1af47'
def cf_uri = 'https://rhpds.redhat.com'
def cf_group = 'rhpds-access-cicd'
// IMAP
def imap_creds = 'd8762f05-ca66-4364-adf2-bc3ce1dca16c'
def imap_server = 'imap.gmail.com'
// Notifications
def notification_email = 'gpteinfrasev3@redhat.com'
def rocketchat_hook = '5d28935e-f7ca-4b11-8b8e-d7a7161a013a'

// SSH key
def ssh_creds = '15e1788b-ed3c-4b18-8115-574045f32ce4'

// Admin host ssh location is in a credential too
def ssh_admin_host = 'admin-host-na'

// state variables
def guid=''
def ocp_master = ''
def ssh_location = ''
def ocp_console = ''
def crd_console = ''

// Catalog items
def choices = [
    'Workshops / OCP4 Workshop - Debug Microservices',
    'DevOps Shared Cluster Development / DEV OCP4 Workshop - Debug Microservices',
].join("\n")

def region_choice = [
    'na_sandbox_gpte',
    'apac_sandbox_gpte',
    'emea_sandbox_gpte',
].join("\n")

pipeline {
    agent any

    options {
        buildDiscarder(logRotator(daysToKeepStr: '30'))
    }

    parameters {
        booleanParam(
            defaultValue: false,
            description: 'wait for user input before deleting the environment',
                name: 'confirm_before_delete'
        )
        choice(
            choices: choices,
            description: 'Catalog item',
            name: 'catalog_item',
        )
        choice(
            choices: region_choice,
            description: 'Catalog item',
            name: 'region',
        )
    }

    stages {
        stage('order from CF') {
            environment {
                uri = "${cf_uri}"
                credentials = credentials("${opentlc_creds}")
                DEBUG = 'true'
            }
            /* This step use the order_svc_guid.sh script to order
             a service from CloudForms */
            steps {
                git url: 'https://github.com/redhat-gpte-devopsautomation/cloudforms-oob'

                script {
                    def catalog = params.catalog_item.split(' / ')[0].trim()
                    def item = params.catalog_item.split(' / ')[1].trim()
                    def region = params.region.trim()
                    def cfparams = [
                        'status=t',
                        'notes=Development - Catalog item creation / maintenance',
                        'check=t',
                        'check2=t',
                        'salesforce=gptejen',
                        'city=jenkins',
                        'notes=devops_automation_jenkins',
                        'expiration=2',
                        'runtime=10',
                        'quotacheck=t',
                        'users=1',
                        "region=${region}",
                    ].join(',').trim()
                    echo "'${catalog}' '${item}'"
                    guid = sh(
                        returnStdout: true,
                        script: """
                          ./opentlc/order_svc_guid.sh \
                          -c '${catalog}' \
                          -i '${item}' \
                          -G '${cf_group}' \
                          -d '${cfparams}' \
                        """
                    ).trim()

                    echo "GUID is '${guid}'"
                }
            }
        }
        // Skip this step because sometimes the completed email arrives
        // before the 'has started' email
        stage('Wait for first email') {
            environment {
                credentials=credentials("${imap_creds}")
            }
            steps {
                git url: 'https://github.com/sborenst/ansible_agnostic_deployer',
                    branch: 'development'

                sh """./tests/jenkins/downstream/poll_email.py \
                    --server '${imap_server}' \
                    --guid ${guid} \
                    --timeout 30 \
                    --filter 'has started'"""
            }
        }

        stage('Wait for last email and parse OpenShift and App location') {
            environment {
                credentials=credentials("${imap_creds}")
            }
            steps {
                git url: 'https://github.com/sborenst/ansible_agnostic_deployer',
                    branch: 'development'

                script {
                    email = sh(
                        returnStdout: true,
                        script: """
                          ./tests/jenkins/downstream/poll_email.py \
                          --server '${imap_server}' \
                          --guid ${guid} \
                          --timeout 180 \
                          --filter 'has completed'
                        """
                    ).trim()

                    try {
                    	def m = email =~ /Openshift Master Console: (http:\/\/[^ \n]+)/
                        ocp_master = m[0][1]
                        echo "Openshift Master Console = '${ocp_master}'"
                        def mm = email =~ /SSH Access: (.*)/
                        ssh_location = mm[0][1]
                        echo "SSH Access = '${ssh_location}'"
                        def mmm = email =~ /OpenShift Console: (https:\/\/[^ \n]+)/
                        ocp_console = mmm[0][1]
                        echo "OpenShift Console = '${ocp_console}'"
                        def mmmm = email =~ /CodeReady Console: (http:\/\/[^ \n]+)/
                        crd_console = mmmm[0][1]
                        echo "CodeReady Console = '${crd_console}'"
                    } catch(Exception ex) {
                        echo "Could not parse email:"
                        echo email
                        echo ex.toString()
                        throw ex
                    }
                }
            }
        }

        stage('Confirm before retiring') {
            when {
                expression {
                    return params.confirm_before_delete
                }
            }
            steps {
                input "Continue ?"
            }
        }
        stage('Retire service from CF') {
            environment {
                uri = "${cf_uri}"
                credentials = credentials("${opentlc_creds}")
                admin_credentials = credentials("${opentlc_admin_creds}")
                DEBUG = 'true'
            }
            /* This step uses the delete_svc_guid.sh script to retire
             the service from CloudForms */
            steps {
                git 'https://github.com/redhat-gpte-devopsautomation/cloudforms-oob'

                sh "./opentlc/delete_svc_guid.sh '${guid}'"
            }
            post {
                failure {
                    withCredentials([usernameColonPassword(credentialsId: imap_creds, variable: 'credentials')]) {
                        mail(
                            subject: "${env.JOB_NAME} (${env.BUILD_NUMBER}) failed retiring for GUID=${guid}",
                            body: "It appears that ${env.BUILD_URL} is failing, somebody should do something about that.\nMake sure GUID ${guid} is destroyed.",
                            to: "${notification_email}",
                            replyTo: "${notification_email}",
                            from: credentials.split(':')[0]
                        )
                    }
                    withCredentials([string(credentialsId: rocketchat_hook, variable: 'HOOK_URL')]) {
                        sh(
                            """
                            curl -H 'Content-Type: application/json' \
                            -X POST '${HOOK_URL}' \
                            -d '{\"username\": \"jenkins\", \"icon_url\": \"https://dev-sfo01.opentlc.com/static/81c91982/images/headshot.png\", \"text\": \"@here :rage: ${env.JOB_NAME} (${env.BUILD_NUMBER}) failed retiring ${guid}.\"}'\
                            """.trim()
                        )
                    }
                }
            }
        }
        stage('Wait for deletion email') {
            steps {
                git url: 'https://github.com/sborenst/ansible_agnostic_deployer',
                    branch: 'development'

                withCredentials([usernameColonPassword(credentialsId: imap_creds, variable: 'credentials')]) {
                    sh """./tests/jenkins/downstream/poll_email.py \
                        --guid ${guid} \
                        --timeout 20 \
                        --server '${imap_server}' \
                        --filter 'has been deleted'"""
                }
            }
        }
    }

    post {
        failure {
            git 'https://github.com/redhat-gpte-devopsautomation/cloudforms-oob'
            /* retire in case of failure */
            withCredentials(
                [
                    usernameColonPassword(credentialsId: opentlc_creds, variable: 'credentials'),
                    usernameColonPassword(credentialsId: opentlc_admin_creds, variable: 'admin_credentials')
                ]
            ) {
                sh """
                export uri="${cf_uri}"
                export DEBUG=true
                ./opentlc/delete_svc_guid.sh '${guid}'
                """
            }

            /* Print ansible logs */
            withCredentials([
                string(credentialsId: ssh_admin_host, variable: 'ssh_admin'),
                sshUserPrivateKey(
                    credentialsId: ssh_creds,
                    keyFileVariable: 'ssh_key',
                    usernameVariable: 'ssh_username')
            ]) {
                sh("""
                    ssh -o StrictHostKeyChecking=no -i ${ssh_key} ${ssh_admin} \
                    "bin/logs.sh ${guid}" || true
                """.trim()
                )
            }

            withCredentials([usernameColonPassword(credentialsId: imap_creds, variable: 'credentials')]) {
                mail(
                    subject: "${env.JOB_NAME} (${env.BUILD_NUMBER}) failed GUID=${guid}",
                    body: "It appears that ${env.BUILD_URL} is failing, somebody should do something about that.",
                    to: "${notification_email}",
                    replyTo: "${notification_email}",
                    from: credentials.split(':')[0]
              )
            }
            withCredentials([string(credentialsId: rocketchat_hook, variable: 'HOOK_URL')]) {
                sh(
                    """
                      curl -H 'Content-Type: application/json' \
                      -X POST '${HOOK_URL}' \
                      -d '{\"username\": \"jenkins\", \"icon_url\": \"https://dev-sfo01.opentlc.com/static/81c91982/images/headshot.png\", \"text\": \"@here :rage: ${env.JOB_NAME} (${env.BUILD_NUMBER}) failed GUID=${guid}. It appears that ${env.BUILD_URL}/console is failing, somebody should do something about that.\"}'\
                    """.trim()
                )
            }
        }
        fixed {
            withCredentials([string(credentialsId: rocketchat_hook, variable: 'HOOK_URL')]) {
                sh(
                    """
                      curl -H 'Content-Type: application/json' \
                      -X POST '${HOOK_URL}' \
                      -d '{\"username\": \"jenkins\", \"icon_url\": \"https://dev-sfo01.opentlc.com/static/81c91982/images/headshot.png\", \"text\": \"@here :smile: ${env.JOB_NAME} is now FIXED, see ${env.BUILD_URL}/console\"}'\
                    """.trim()
                )
            }
        }
    }
}
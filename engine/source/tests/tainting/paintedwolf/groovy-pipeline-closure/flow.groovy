pipeline {
  stages {
    stage('Build') {
      steps {
        // ruleid: flow
        sh "echo ${params.INPUT}"
        sh 'echo ${params.INPUT}'
        sh "echo fixed"
      }
    }
  }
}

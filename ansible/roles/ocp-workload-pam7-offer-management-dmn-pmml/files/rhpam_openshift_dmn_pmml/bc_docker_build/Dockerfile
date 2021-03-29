FROM registry.redhat.io/rhpam-7/rhpam-businesscentral-rhel8:7.9.0

# jPMML
ADD https://search.maven.org/remotecontent?filepath=org/jpmml/pmml-evaluator/1.4.9/pmml-evaluator-1.4.9.jar /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-1.4.9.jar
ADD https://search.maven.org/remotecontent?filepath=org/jpmml/pmml-evaluator-extension/1.4.9/pmml-evaluator-extension-1.4.9.jar /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-extension-1.4.9.jar
ADD https://search.maven.org/remotecontent?filepath=org/kie/kie-dmn-jpmml/7.27.0.Final/kie-dmn-jpmml-7.27.0.Final.jar /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/kie-dmn-jpmml-7.27.0.Final.jar

USER root
RUN chown jboss:root /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-1.4.9.jar && \
			chown jboss:root /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-extension-1.4.9.jar && \
      chown jboss:root /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/kie-dmn-jpmml-7.27.0.Final.jar && \
			chmod 664 /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-1.4.9.jar && \
			chmod 664 /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-extension-1.4.9.jar && \
      chmod 664 /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/kie-dmn-jpmml-7.27.0.Final.jar

USER jboss

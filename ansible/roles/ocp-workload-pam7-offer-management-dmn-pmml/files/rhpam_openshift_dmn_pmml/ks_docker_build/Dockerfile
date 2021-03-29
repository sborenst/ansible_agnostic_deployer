FROM docker-registry.default.svc:5000/openshift/rhpam-kieserver-rhel8:7.9.0

# jPMML
ADD https://search.maven.org/remotecontent?filepath=org/jpmml/pmml-evaluator/1.4.9/pmml-evaluator-1.4.9.jar /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-1.4.9.jar
ADD https://search.maven.org/remotecontent?filepath=org/jpmml/pmml-evaluator-extension/1.4.9/pmml-evaluator-extension-1.4.9.jar /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-extension-1.4.9.jar
ADD https://search.maven.org/remotecontent?filepath=org/kie/kie-dmn-jpmml/7.27.0.Final/kie-dmn-jpmml-7.27.0.Final.jar /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/kie-dmn-jpmml-7.27.0.Final.jar

COPY contrib/jbpm-event-emitters-elasticsearch-7.36.0-SNAPSHOT.jar /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/jbpm-event-emitters-elasticsearch-7.36.0-SNAPSHOT.jar
COPY contrib/rhpam-case-mgmt-showcase.war /opt/eap/


USER root
RUN chown jboss:root /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-1.4.9.jar && \
			chown jboss:root /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-extension-1.4.9.jar && \
      chown jboss:root /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/kie-dmn-jpmml-7.27.0.Final.jar && \
			chown jboss:root /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/jbpm-event-emitters-elasticsearch-7.36.0-SNAPSHOT.jar && \
			chmod 664 /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-1.4.9.jar && \
			chmod 664 /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/pmml-evaluator-extension-1.4.9.jar && \
      chmod 664 /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/kie-dmn-jpmml-7.27.0.Final.jar && \
			chmod 664 /opt/eap/standalone/deployments/ROOT.war/WEB-INF/lib/jbpm-event-emitters-elasticsearch-7.36.0-SNAPSHOT.jar

USER jboss

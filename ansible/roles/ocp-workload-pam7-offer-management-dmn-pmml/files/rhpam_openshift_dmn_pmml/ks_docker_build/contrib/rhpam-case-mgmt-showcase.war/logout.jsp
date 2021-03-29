<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ page import="org.slf4j.Logger" %>
<%@ page import="org.slf4j.LoggerFactory" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<%
    final Logger logger = LoggerFactory.getLogger( "logout.jsp" );
    try {
        request.logout();
        javax.servlet.http.HttpSession httpSession = request.getSession(false);
        if (httpSession != null) {
            httpSession.invalidate();
        }
    } catch ( SecurityException e ) {
        //The only case we know that this  happens is when java security manager is enabled on EAP.
        logger.debug( "Security exception happened, without consequences, during logout.", e );
    }
%>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" class="login-pf">
<head>
    <link rel="stylesheet" href="<%=request.getContextPath()%>/org.jbpm.workbench.cm.jBPMCaseManagement/css/patternfly.min.css">
    <link rel="stylesheet" href="<%=request.getContextPath()%>/org.jbpm.workbench.cm.jBPMCaseManagement/css/patternfly-additions.min.css">
    <link rel="stylesheet" href="<%=request.getContextPath()%>/org.jbpm.workbench.cm.jBPMCaseManagement/css/showcase.css">
    <link rel="shortcut icon" href="favicon.png"/>
    <title>Sample Case Management App</title>
</head>
<body>
    <span id="badge">
        <img src="<%=request.getContextPath()%>/org.jbpm.workbench.cm.jBPMCaseManagement/img/logo.png" />
    </span>
    <div class="container">
        <div class="row">
            <div class="col-sm-7 col-md-6 col-lg-5 login">
                <div class="alert alert-success">
                    <span class="pficon pficon-ok"></span>
                    <strong>Logout successful</strong>
                </div>
                <form class="form-horizontal" role="form" action="<%= request.getContextPath() %>/jbpm-cm.html" method="POST">
                    <div class="form-group">
                        <div class="col-xs-offset-8 col-xs-4 col-sm-offset-8 col-sm-4 col-md-offset-8 col-md-4 submit">
                            <button type="submit" class="btn btn-primary btn-lg" tabindex="1">Login again</button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</body>
</html>

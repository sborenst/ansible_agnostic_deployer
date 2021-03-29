<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<%
    request.getSession().invalidate();
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
                <div class="alert alert-danger">
                    <span class="pficon pficon-error-circle-o"></span>
                    <strong>Login failed: Not Authorized</strong>
                </div>
                <form class="form-horizontal" role="form" action="<%= request.getContextPath() %>/jbpm-cm.html" method="GET">
                    <div class="form-group">
                        <div class="col-xs-offset-8 col-xs-4 col-sm-offset-8 col-sm-4 col-md-offset-8 col-md-4 submit">
                            <button type="submit" class="btn btn-primary btn-lg" tabindex="1">Login as another user</button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</body>
</html>

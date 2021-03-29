<%
  String queryString = request.getQueryString();
  String redirectURL = request.getContextPath()  +"/login?"+(queryString==null?"":queryString);
  response.sendRedirect(redirectURL);
%>
use CGI;
my $value=CGI::param("code");
# ruleid: flow
eval("print $value");
eval { print $value };
eval('print $value');

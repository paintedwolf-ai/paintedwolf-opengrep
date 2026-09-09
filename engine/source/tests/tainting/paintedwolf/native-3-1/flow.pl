use CGI;
my $value=CGI::param("code");
# ruleid: flow
system($value);
system("printf", "%s", $value);

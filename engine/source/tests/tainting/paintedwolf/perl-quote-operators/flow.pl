my $value = CGI::param("code");
# ruleid: flow
eval qq(print $value);
eval q(print $value);
eval "print \$value";
# ruleid: flow
eval "print ${value}";
# ruleid: flow
eval "print $value";
# ruleid: flow
my $text = `echo $value`;
# ruleid: flow
my $quoted = qx(echo $value);
my $literal = qx'echo $value';
# ruleid: flow
system("echo $value");
system("printf", "%s", $value);
# ruleid: flow
open(my $fh, $value);
open(my $fh2, "<", $value);
my %fields = ('don\'t' => CGI::param("code"));
# ruleid: flow
eval($fields{"don't"});

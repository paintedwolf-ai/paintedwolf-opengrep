my %items = (value => source(), safe => "constant");
# ruleid: flow
sink($items{value});
# ruleid: flow
sink($items{'value'});
sink($items{safe});
my $items = "separate scalar";
sink($items);
$items{value} = "overwritten";
sink($items{value});
my @list = (source(), "constant");
# ruleid: flow
sink($list[0]);
sink($list[1]);
my $reference = {value => source(), safe => "constant"};
# ruleid: flow
sink($reference->{value});
sink($reference->{safe});
{
  my %items = (value => source());
  # ruleid: flow
  sink($items{value});
}
sink($items{value});
my %outer = (value => source());
{
  my %outer = (value => "local");
  sink($outer{value});
}
# ruleid: flow
sink($outer{value});
{
  my %outer;
  sink($outer{value});
}
# ruleid: flow
sink($outer{value});
my % braced = (value => source());
# ruleid: flow
sink(${braced}{value});
# ruleid: flow
sink($ braced {'value'});
my $ braced = "separate scalar";
sink(${braced});
my ${value} = source();
# ruleid: flow
sink($ value);

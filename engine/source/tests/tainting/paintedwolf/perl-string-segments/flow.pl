# ruleid: prefix
inspect("prefix $value suffix");
# ruleid: prefix
inspect(qq(prefix ${value} suffix));
inspect("different $value suffix");
inspect("prefix $value different");
inspect("$value");
inspect(q(prefix $value suffix));
inspect("prefix \$value suffix");

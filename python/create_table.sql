create table streamed_stats(accountname varchar, statsname varchar, count bigint default 0.0, m1
	double precision default 0.0, m2 double precision default 0.0, m3 double precision default
	0.0, m4 double precision default 0.0, primary key(accountname, statsname))
;

create table sampled_values(accountname varchar, statsname varchar, value double precision,
	foreign key (accountname, statsname) references streamed_stats(accountname, statsname)
);


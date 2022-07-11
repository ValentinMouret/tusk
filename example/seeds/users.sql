insert into "user"
            (id, name, birth_date)
     values (1, 'Valentin', '1995-08-15'),
            (2, 'Baruch', '1632-11-24')
on conflict (id)
  do update
        set id=excluded.id,
            name=excluded.name,
            birth_date=excluded.birth_date;

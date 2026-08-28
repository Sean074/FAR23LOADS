- **The %MAC ↔ fuselage-station Tool no longer reinterprets its entered station
  on a unit switch (#126, tier S, 2026-08-28; production-release review §3.4).**
  The station field was the one converted number input in either GUI spelled by
  hand instead of through `app_shell.components.unit_number_input`: seeded with a
  converted length but keyed without the system suffix `number_input_name`
  appends on the converted path, so Streamlit's retained state outvoted `value=`
  and the same digits were read as inches on one render and as millimetres on
  the next — on `ga6_normal`, 63.641 answered **0.00 % MAC** in Imperial and
  **−88.29 % MAC** after toggling to SI, the same field, the same number, two
  answers. It now goes through the one unit boundary like every other converted
  number, so a switch re-seeds the field with the leading edge in the new unit.
  Display-only, so nothing was stored and no load moved. Two behavioural guards
  drive the real unit radio (the four tests #80 shipped with all run Imperial,
  which is why nothing caught it): the tool's answer follows the physical
  station in either system, and the field re-seeds rather than being reread —
  the second fails on the pre-fix code. Practice 4 takes the class with them: a
  source guard across `app_shell/`, `oracle_app/` and `app/views/` fails any
  `st.number_input` seeded with a converted value whose key does not carry the
  active system, with the two pre-`unit_number_input` key helpers it tolerates
  checked rather than trusted.

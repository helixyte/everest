


Querying
========

An incoming query is processed by :mod:`everest` in two steps: First, the query
string submitted by the client is parsed into a query specification; and
second, this query specification is translated to an object that can be applied
to the collection resource acting as the query context.


Query Language
==============

:mod:`everest` supports a custom Collection Query Language (CQL) for querying
collection resources.


CQL query expressions are composed of one or more query criteria separated by
the tilde ("~") character. Each criterion consists of three parts separated by
a colon (":") character :

1. resource attribute name
  Specifies the name of the resource to query. You can specify dotted names
  to query nested resources (see xxx).
2. operator
  The operator to apply.
3. value
  The value to query for. Criteria values are given as literal representations

As an example, querying a collection resource ""

.. code-block: text

name:starts-with:J



The following table shows the available operators and data types in CQL:


=========================  ======== ====== ========= ========
     Operator                         Data Type
                           -------- ------ --------- --------
                            String  Number Date/Time Resource
=========================  ======== ====== ========= ========
    ``starts-with``            x
  ``not-starts-with``          x
    ``ends-with``              x
  ``not-ends-with``            x
    ``contains``               x
  ``not-contains``             x
   ``contained``               x
 ``not-contained``             x
    ``equal-to``
  ``not-equal-to``
    ``less-than``
``less-than-or-equal-to``
   ``greater-than``
``greater-than-or-equal-to``
     ``in-range``





It is by design that the power of CQL to express complex queries is far behind
that of SQL.
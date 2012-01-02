


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
  The value to query for. It is possible to supply multiple
  values in a comma separated list, which will be interpreted as a Boolean
  "OR" operation on all given values.


Supported criterion value types are:

String
   Arbitrary string enclosed in double quotes.
Number
   Integer or floating point, scientific notation allowed.
Boolean
   Case insensitive string **true** or **false**.
Date/Time
   ISO 8601 encoded string enclosed in double quotes.
Resource
   URL referencing a resource.

As an example, querying a collection resource ""

.. code-block: text

name:starts-with:J

If a query contains multiple criteria with different resource attribute names,
the criteria are interpreted as a Boolean "AND" operation.

The following table shows the available operators and data types in CQL:


=========================  ======== ====== ======= ========== ========
     Operator                             Data Type
                           -------- ------ ------- --------- --------
                            String  Number Boolean Date/Time Resource
=========================  ======== ====== ======= ========= ========
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



All attributes that are used to compose a query expression need to be mapped
column properties in the ORM. Aliases are supported, CompositeProperties are 
not. All queried entities must have an "id" attribute.

It is by design that the power of CQL to express complex queries is far behind
that of SQL.
Resources
#########

Slugs
*****

In a member URL such as
``, the last part which identifies the member uniquely within its parent collection resource is called a "slug". When :mod:`everest` resolves a given member URL to a member object, it builds a query that looks up the member's entity in the collection's aggregate, using the slug as the search key. To be able to use the slug in query expressions, it needs to be declared at the entity data model level; there are two choices for implemeting this:

 1) If you want your users to be able to customize
the slugs for individual member resources, then you will have to add a "slug"
field to your entity class and map that to an appropriate column at the ORM
layer.
 2) Alternatively, you can use one or more other persistent columns from
the entity to define a (read-only) slug expression.


Nested attributes
*****************


Handling complex entity models
******************************

Complex entity models are rarely exposed fully to a client application. Rather,
nested data structures

Sometimes, you want to hide the complexity of your entity model from the client.

One way of providing access to nested  doing this is to add "shortcut"
 attributes to your entities that
provide direct access to nested data structures, e.g. at the ORM layer.

Obviously, this solution is not very elegant as it introduces unnecessary
attributes to your entity objects.

:mod:`everest` offers another approach by allowing the definition of such
shortcuts through dotted attribute notation. The only requirement is that the
endpoint

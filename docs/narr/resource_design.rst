Resource Design
===============

Entities and resources
----------------------

:mod:`everest` applications keep their value state in entity objects which
are mapped to a persistency backend through the :mod:`sqlalchemy`
ORM. This entity model implements the *domain logic* of the application by
enforcing all value state constraints at all times.

A resource object makes a part of the entity model available for
manipulations such as updating existing or creating new entities, thus
implementing the *business logic* of the application.

Following the path laid out in the excellent "REST in Practice" book,
:mod:`everest` web service applications use the ATOM Publishing Protocol
(AtomPub) at the core.


Collection resources and aggregates
-----------------------------------

The same way that sets of member resources of the same type are held in a
collection resource, sets of entities of the same type are held in an
*aggregate*. An aggregate roughly corresponds to a table in a relational
database; it can either be


Exposing entity attributes in resources
---------------------------------------

There are three kinds of resource attributes in :mod:`everest`: Terminal
attributes, member attributes, and collection attributes. A *terminal*
resource attribute references an object of an atomic type or some other type
the :mod:`everest` framework does not know more about. A *member* resource
attribute references another member resource and a *collection* resource
attribute references another collection resource.

Resource attributes are declared using the :function:`terminal_attribute`,
:function:`member_attribute`, and :function:`collection_attribute` descriptor
generating functions from the :mod:`resources.descriptors` module. Only
attributes declared with these descriptors will be accessible through a
resource.


Nested attributes
-----------------


Handling complex entity models
------------------------------

Sometimes, you need to hide the complexity of your entity model from
the client.

One way of doing this is to add "shortcut" attributes to your entities, e.g.
at the ORM layer.

Obviously, this solution is not very elegant as it introduces unnecessary
attributes to your entity objects.

:mod:`everest` offers another approach by allowing the definition of such
shortcuts through dotted attribute notation. The only requirement is that
the endpoint

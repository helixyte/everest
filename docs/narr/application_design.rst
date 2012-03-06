In this section, you will find a step-by-step guide on how to design a RESTful
application with :mod:`everest`.

1. The application

Suppose you want to write a program that helps a garden designer with composing
lists of beautiful perennials and shrubs that she intends to plant in her
customer's gardens. Let's call this fancy application "Plant Scribe". In its
simplest possible form, this application will have to handle customers,
projects (per customer), sites (per project), and lists of plant species (one
per site).


2. Design the entity model

First, we decide which data we want to store in our entity model. We start
with the customer:

.. literalinclude:: ../demoapp/v0/plantscribe/entities/customer.py
   :lineno: 

In our example, the :class:`Customer` class inherits from the :class:`Entity`
class provided by :mod:`everest`. This is convenient, but not necessary; any
class can participate in the entity model as long as it implements the
:class:`everest.entities.interfaces.IEntity` interface. Note, however, that
this interface requires the presence of a ``slug`` attribute, which in the case
of the customer entity is composed of the concatenation of the customer's last
and first name.

For each customer, we need to be able to handle an arbitrary number of
projects:

.. literalinclude:: ../demoapp/v0/plantscribe/entities/project.py
   :lineno: 

Note that while the project references the customer, we do not (yet) have a way
to access the projects associated with a given customer as an attribute of its
customer entity. While avoiding such circular references allows us to keep our
entity model simple, we might miss the convenience they offer. We will return
to this issue a little later.

Each project is referenced by one or more planting sites:

.. literalinclude:: ../demoapp/v0/plantscribe/entities/site.py
   :lineno: 

The plant species we can use at each site are modeled as follows:

.. literalinclude:: ../demoapp/v0/plantscribe/entities/species.py
   :lineno: 

Finally, the information about which plant species to use at which site and in
which quantity is modeled as an "incidence" entity:

.. literalinclude:: ../demoapp/v0/plantscribe/entities/incidence.py
   :lineno:


3. Design the resource layer

With the entity model in place, we can  now proceed to designing the resource
layer. The first step here is to define the marker interfaces that
:mod:`everest` will use to access the various parts of the resource system.
This is very straightforward to do:

.. literalinclude:: ../demoapp/v0/plantscribe/interfaces.py
   :lineno:

Next, we write the member resource classes. This is where we decide which
attributes of the entity model will be accessible from the outside and how
they will be exposed. In our basic example, the resources mostly declare the
public attributes of the underlying entities as attributes using the
:func:`member_attribute` descriptor for member resource attributes,
the :func:`collection_attribute` descriptor for collection resource
attributes and the :func:`terminal_attribute` for non-resource attributes:

.. literalinclude:: ../demoapp/v0/plantscribe/resources/customer.py
   :lineno:

.. literalinclude:: ../demoapp/v0/plantscribe/resources/project.py
   :lineno:

.. literalinclude:: ../demoapp/v0/plantscribe/resources/site.py
   :lineno:

.. literalinclude:: ../demoapp/v0/plantscribe/resources/species.py
   :lineno:

.. literalinclude:: ../demoapp/v0/plantscribe/resources/incidencde.py
   :lineno:

In the simple case where the resource attribute descriptor declares a public
attribute of the underlying entity, it expects a type or an interface of the
target object and the name of the corresponding entity attribute as arguments.

For :func:`member_attribute` and :func:`collection_attribute` descriptors there
is also an optional argument `is_nested`, which determines if the URL for the
target resource is going to be formed relative to the root (i.e., as an
absolute path) or relative to the parent resource declaring the attribute.


.. sidebar:: URL resolution
   
   :mod:`everest` favors and facilitates object traversal for URL resolution. 
   In particular, all resource attributes that target a member or collection
   resource can be used directly for URL traversal. 
   

We also have the possibility to declare resource attributes that do not
reference the target resource directly through an entity attribute, but
indirectly through a "backreferencing" attribute. This is how we can now
have the :class:`CustomerMember` resource have a 'projects'
attribute linking to a collection resource for :class:`IProject` by means
of the "customer" Add 'backreference' to dictionary, even though,
as noted above, the underlying :class:`Customer` entity is not linked to
its sequence of :class:`Project` entities.


4. Configuring the application

With the resource layer in place, we can now move on to configuring our
application. :mod:`everest` applications are based on the :mod:`pyramid`
framework and everything you learned about configuring :mod:`pyramid`
applications can be applied here. Rather than duplicating the excellent
documentation available on the Pyramid web site, we will focus on a minimal
example on how to configure the extra resource functionality that
:mod:`everest` supplies.

The minimal ``.ini`` file for the ``plantscribe`` application looks like this:

.. literalinclude:: ../demoapp/v0/plantscribe/plantscribe.ini

The ``.zcml`` configuration file is more interesting:

.. literalinclude:: ../demoapp/v0/plantscribe/configure.zcml
   :lineno:

Not the ``include`` directive at the top of the file; this not only pulls in the
:mod:`everest`-specific ZCML directives, but also the Pyramid directives as
well.

 The most important of the :mod:`everest`-specific directives is the
 ``resource`` directive. This sets up the connections between the various parts
 of the resource subsystem, using our marker interfaces as the glue. At the
 minimum, you need to specify

- A marker interface for your resource;

- An entity class for the resource;

- A member class class for the resource; and

- A name for the root collection.

The aggregate and collection objects needed by the resource subsystem (cf. xxx)
are created automatically; you may, however, supply a custom collection class
that inherits from :class:`everest.resources.base.Collection`. If you do not
plan on exposing the collection for this resource to the outside, you can set
the ``expose`` flag to ``false``, in which case you do not need to provide a
root collection name.









5. Adding persistency



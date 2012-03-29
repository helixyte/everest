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

First, we decide which data we want to store in our entity model. We start with
the customer:

.. literalinclude:: ../demoapp/v0/plantscribe/entities/customer.py
   :lineno: 

In our example, the :class:`Customer` class inherits from the :class:`Entity`
class provided by :mod:`everest`. This is convenient, but not necessary; any
class can participate in the entity model as long as it implements the
:class:`everest.entities.interfaces.IEntity` interface. Note, however, that
this interface requires the presence of a ``slug`` attribute, which in the case
of the customer entity is composed of the concatenation of the customer's last
and first name.

For each customer, we need to be able to handle an arbitrary number of projects:

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
attributes of the entity model will be accessible from the outside and how they
will be exposed. In our basic example, the resources mostly declare the public
attributes of the underlying entities as attributes using the
:func:`member_attribute` descriptor for member resource attributes, the
:func:`collection_attribute` descriptor for collection resource attributes and
the :func:`terminal_attribute` for non-resource attributes:

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
indirectly through a "backreferencing" attribute. This is how we can now have
the :class:`CustomerMember` resource have a 'projects' attribute linking to a
collection resource for :class:`IProject` by means of the "customer" Add
'backreference' to dictionary, even though, as noted above, the underlying
:class:`Customer` entity is not linked to its sequence of :class:`Project`
entities.


4. Configuring the application

With the resource layer in place, we can now move on to configuring our
application. :mod:`everest` applications are based on the :mod:`pyramid`
framework and everything you learned about configuring :mod:`pyramid`
applications can be applied here. Rather than duplicating the excellent
documentation available on the Pyramid web site, we will focus on a minimal
example on how to configure the extra resource functionality that
:mod:`everest` supplies.

The minimal ``.ini`` file for the ``plantscribe`` application is quite simple:

.. literalinclude:: ../demoapp/v0/plantscribe.ini

The only purpose of the ``.ini`` file is to specify a ``Paster`` application
factory which is responsible for creating and setting up the application
registry and for instantiating a WSGI application.

The ``.zcml`` configuration file - which is loaded through the application
factory - is more interesting:

.. literalinclude:: ../demoapp/v0/plantscribe/configure.zcml
   :lineno:

Note the ``include`` directive at the top of the file; this not only pulls in
the :mod:`everest`-specific ZCML directives, but also the Pyramid directives as
well.

The most important of the :mod:`everest`-specific directives is the ``resource``
directive. This sets up the connections between the various parts of the
resource subsystem, using our marker interfaces as the glue. At the minimum,
you need to specify

- A marker interface for your resource;

- An entity class for the resource;

- A member class class for the resource; and

- A name for the root collection.

The aggregate and collection objects needed by the resource subsystem (cf. xxx)
are created automatically; you may, however, supply a custom collection class
that inherits from :class:`everest.resources.base.Collection`. If you do not
plan on exposing the collection for this resource to the outside, you can set
the ``expose`` flag to ``false``, in which case you do not need to provide a
root collection name. Non-exposed resources will still be available as a root
collection internally, but access through the service as well as the
genereation of absolute URLs will not work.


5. Running the application

To see our little application in action, we can use the ``pshell`` interactive
shell that comes with ``Pyramid``. First, install the ``plantscribe`` package
by issuing

.. code-block:: text
   $ pip -e .
   
inside the ``docs/demoapp/v0`` folder of the :mod:`everest` source tree. This
presumes you have followed the instructions of installing :mod:`everest` and
use a ``virtualenv`` with the ``pip`` installer (cf. xxx).

Now, still from the same directory, you start the ``Pyramid`` ``pshell`` like
this:

.. code-block:: text

   $ pshell plantscribe.ini 
   Python 2.7.2 (v2.7.2:8527427914a2, Jun 11 2011, 15:22:34)
   [GCC 4.2.1 (Apple Inc. build 5666) (dot 3)] on darwin
   Type "help" for more information.
   
   Environment:
     app          The WSGI application.
     registry     Active Pyramid registry.
     request      Active request object.
     root         Root of the default resource tree.
     root_factory Default root factory used to create `root`.

   >>> 

The ``root`` object that is available in the ``pshell`` environment is the
service object that provides access to all public root collections by name:

.. code-block:: text

   >>> c = root['customers']
   >>> c 
   <CustomerMemberCollection name:customers parent:Service(started)>

We can now start adding members to the collection and retrieve them back from
the collection:

.. code-block:: text

   >>> from plantscribe.entities.customer import Customer
   >>> ent = Customer('Peter', 'Fox')
   >>> m = c.create_member(ent)
   >>> m.__name__
   'fox-peter'
   >>> c.get('fox-peter').__name__
   'fox-peter'


6. Adding persistency

With the application running, we now turn our attention to persistency.
:mod:`everest` uses a *repository* to load and save resources from and to a
storage backend. To use a filesystem-based repository as the default for our
application, we could use the following ZCML declaration:

.. code-block:: text

   <filesystem_repository
      directory="data"
      content_type="everest.mime.CsvMime"
      make_default="true" />

This tells :mod:`everest` to use the ``data`` directory (relative to the
``plantscribe`` package) to persist representations of the root collections of
all resources as ``.csv`` files. When the application is initialized, the root
collections are loaded from these representation files and during each
``commit`` operation at the end of a transaction, all modified root collections
are written back to their corresponding representation files.

The filesystem-based repository does not perform well with complex or high
volume data structures or in cases where several processes need to access the
same persistency backend. In these situations, we need to switch to a an
ORM-based repository. :mod:`everest` uses xxx ``SQLAlchemy`` as ORM. What
follows is a highly simplified account of what is needed to instruct
``SQLAlchemy`` to persist the entities of an :mod:`everest` application; for an
explanation of the terms and concepts used in this section, please refer to the
excellent documentation on the ``SQLAlchemy`` web site.

In a first step, we need to initialize the ORM. The following ZCML declaration
makes the ORM the default resource repository:

.. code-block:: text

    <orm_repository
        metadata_factory="everest.tests.testapp_db.db.create_metadata"
        make_default="true"/>

The metadata factory setting references a callable that takes an ``SQLAlchemy``
engine as a parameter and returns a fully initialized metadata instance. For
our simple application, this function looks like this:

.. literalinclude:: ../demoapp/v0/plantscribe/orm.py
   :lineno:

The function first creates a database schema and then maps our entity classes to
this schema.


To use an engine other than the default in-memory SQLite database engine, you
need to supply a ``db_string`` setting in the paster application ``.ini`` file.
For example:

.. code-block::text

   [DEFAULT]
   db_server = mydbserver
   db_port = 5432
   db_user = mydbuser
   db_password = mypassword
   db_name = mydbname
   
   [app:myapp]
   db_string = postgresql+psycopg2://%(db_user)s:%(db_password)s@%(db_server)s:%(db_port)s/%(db_name)s
   

Different resorces may use different repositories, but any given resource can
only be assigned one repository.
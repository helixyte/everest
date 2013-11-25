======================================
everest - REST applications for python
======================================


``everest`` is an extension of the popular
`Pyramid <http://www.pylonsproject.org/>`_ framework aimed at simplifying the
development of REST applications in `Python <http://www.python.org>`_.

``everest`` features in a nutshell:

* A resource declaration framework that allows you to expose an entity domain
  model through a REST application;
* Extensible views for performing standard CRUD operations on resources in
  response to REST requests;
* Representers that convert resources to string representations and vice versa
  for a number of MIME types (XML, ATOM, CSV, JSON);
* A repository layer with four different storage backends: a memory backend, a
  file system backend, a NoSQL database backend and a relational database
  backend;
* A query language for expressing complex hierarchical queries on the resource
  object tree through URLs;
* A Flex client
  (`distributed separately <https://github.com/cenix/everest-flex>`_).


Installation
============

Installing ``everest`` is simple. You need

* A recent version of Python (2.7.x). See
  `here <http://www.python.org/download/releases/2.7.3/>`_ for instructions;
* The pip Python package installer. Install in a shell with the command

  .. code-block:: console

     > easy_install pip

With these requirements in place, all you need to do to install ``everest`` is
to issue the command

.. code-block:: console

   > pip install everest


Documentation
=============

* `API documentation <http://cenix.github.com/everest/api.html>`_
* A `demo application <http://cenix.github.com/everest-demo>`_.


Development
===========

``everest`` is hosted on `github <https://github.com/cenix/everest>`_. To
contribute, please fork the project and submit a pull request. Please adhere to
PEP8 in your code and ensure 100% test coverage and zero pylint errors and
warnings (using the configuration file supplied in the `support` directory).

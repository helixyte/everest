======================================
everest - REST applications for python
======================================


`everest` is an extension of the popular `Pyramid` framework aimed at
simplifying the development of REST applications.

`everest` features in a nutshell:

 * A resource declaration framework that allows you to expose an entity domain
   model through a REST application;
 * Extensible views for performing standard CRUD operations on resources in
   response to REST requests;
 * Representers that convert resources to string representations and vice
   versa for a number of MIME types (XML, ATOM, CSV, JSON);
 * A repository layer permitting per-resource configuration of the storage
   backend to use (memory for testing, file system for small data volumes,
   relational database for large data volumes);
 * A query language for expressing complex hierarchical queries on the
   resource object tree through URLs;
 * A Flex client
   (`distributed separately <https://github.com/cenix/everest-flex>`_).


Installation
============

Installing `everest` is simple:

.. code-block:: console

   > pip install everest


Documentation
=============

`everest` comes complete with
 * `API documentation <http://cenix.github.com/everest/api.html>`_ and
 * a `demo application <http://cenix.github.com/everest-demo>`_.


Development
===========

`everest` is hosted on `github <https://github.com/cenix/everest>`_. To
contribute, please fork the project and submit a pull request. Please adhere
to PEP8 in your code and ensure 100% test coverage. We recommend configuring
pylint with the configuration file supplied in the `support` directory.

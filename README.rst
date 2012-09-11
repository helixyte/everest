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
 * A Flex client (distributed separately; see
   https://github.com/cenix/everest-flex).

`everest` comes complete with a tutorial and a demo application. Code
quality is strictly controlled using continuous integration, pylint and 100%
test coverage.

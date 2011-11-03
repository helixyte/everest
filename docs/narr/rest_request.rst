Anatomy of a REST Request
=========================

When a REST call is made from a client, :mod:`everest` first follows the
standard :mod:`BFG` request processing chain: The context for the request is
found through object graph traversal and the best matching view is looked up
and dispatched, passing the request and the context as arguments.

:mod:`everest` provides views for the "Uniform Interface" REST operations on
resources, namely for GET, PUT, POST and DELETE requests on resource
collections and members. Unlike in pure :mod:`BFG` applications where the
view acts as a controller, the responsibility of the view is reduced to
dispatching the correct resource operation and preparing the context for
rendering the response.


request  context
GET      collection
GET      member
POST     collection
PUT      member

A GET request to a collection resource is processed by the `getcollectionview`
view as follows:

1. The query parameter is extracted from the request, if present. Query
   parameters are CQL expressions which are converted to a ORM query and
   attached to the context (collection) resource.
2. The sort parameter is extracted from the request, if present.
3. The slice parameters are extracted from the request, if present.


A PUT request to a member resource is processed by the `putmemberview` view as
follows:

1. A representer is created from the MIME content type of the incoming
   representation and the interface implemented by the context.
2. The representation contained in the body of the request is converted to
   a resource by the representer.
3. The `update` method of the context (member) resource is called with the
   new de-serialized resource as argument.
4. The udpated member resource is converted to the MIME content type requested
   by the client and returned.
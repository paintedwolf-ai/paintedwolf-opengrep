(use-modules ((web.request) #:select (request-uri)))
(define (handler request) (sink (request-uri request)))

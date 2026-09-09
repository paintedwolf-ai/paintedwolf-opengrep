(use-modules ((web request) #:select (request-uri)))
(define (handler request)
  (set! request-uri (lambda (r) "fixed"))
  (sink (request-uri request)))

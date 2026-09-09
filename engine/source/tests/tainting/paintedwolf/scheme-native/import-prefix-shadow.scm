(use-modules ((web request) #:prefix http:))
(define (handler request)
  (let ((http:request-uri (lambda (r) "fixed"))) (sink (http:request-uri request))))

(use-modules ((web request) #:prefix http:))
(define (handler request)
  ;; ruleid: flow
  (sink (http:request-uri request))
  (sink (request-uri request)))

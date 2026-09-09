(ns app (:require [framework.http :as web]))
;; ruleid: flow
(sink (web/source))
(let [web {:source "local"}]
  ;; ruleid: flow
  (sink (web/source)))
(sink '(web/source))
(sink "(web/source)")
(ns other (:require [unrelated.http :as web]))
(sink (web/source))
(ns third)
(sink (web/source))
;; ruleid: flow
(sink (framework.http/source))

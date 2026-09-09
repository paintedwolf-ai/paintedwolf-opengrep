(ns first (:require [example.api :as api]))
;; ruleid: namespace-alias
(api/read-input)
(let [api {:read-input "local value"}]
  ;; ruleid: namespace-alias
  (api/read-input))
;; ok: namespace-alias
'(api/read-input)
;; ok: namespace-alias
"(api/read-input)"
(ns second (:require [unrelated.api :as api]))
;; ok: namespace-alias
(api/read-input)
(ns third)
;; ok: namespace-alias
(api/read-input)
;; ruleid: namespace-alias
(example.api/read-input)
(ns fourth (:require [example.api :as api]))
(ns-unalias *ns* 'api)
;; ok: namespace-alias
(api/read-input)
(ns fifth (:require [example.api :as api]))
(alias 'api 'unrelated.api)
;; ok: namespace-alias
(api/read-input)

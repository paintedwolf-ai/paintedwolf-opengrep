(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn [enabled] (if enabled value "safe"))] (helper false) (sink (helper true))))
(register handler)

(defn handler [value]
;; ok: closure-context
 (let [helper (fn [ignored enabled] (if enabled value "safe"))] (sink (helper value false))))
(register handler)

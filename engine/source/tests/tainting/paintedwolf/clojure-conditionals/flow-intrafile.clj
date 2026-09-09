;; ruleid: flow
(when true (sink (source)))
(when false (sink (source)))
(when nil (sink (source)))
;; ruleid: flow
(when 0 (sink (source)))
;; ruleid: flow
(when "" (sink (source)))
;; ruleid: flow
(when [] (sink (source)))
(when-not true (sink (source)))
;; ruleid: flow
(when-not false (sink (source)))
;; ruleid: flow
(when-not nil (sink (source)))
(when-not 0 (sink (source)))
(when-not "" (sink (source)))
(when-not [] (sink (source)))
(if-not true (sink (source)))
;; ruleid: flow
(if-not false (sink (source)))
;; ruleid: flow
(if-not nil (sink (source)))
(if-not 0 (sink (source)))
(if-not "" (sink (source)))
(if-not [] (sink (source)))
;; ruleid: flow
(when-let [x true] (sink (source)))
(when-let [x false] (sink (source)))
(when-let [x nil] (sink (source)))
;; ruleid: flow
(when-let [x 0] (sink (source)))
;; ruleid: flow
(when-let [x ""] (sink (source)))
;; ruleid: flow
(when-let [x []] (sink (source)))
;; ruleid: flow
(when-some [x true] (sink (source)))
;; ruleid: flow
(when-some [x false] (sink (source)))
(when-some [x nil] (sink (source)))
;; ruleid: flow
(when-some [x 0] (sink (source)))
;; ruleid: flow
(when-some [x ""] (sink (source)))
;; ruleid: flow
(when-some [x []] (sink (source)))
;; ruleid: flow
(if-let [x true] (sink (source)))
(if-let [x false] (sink (source)))
(if-let [x nil] (sink (source)))
;; ruleid: flow
(if-let [x 0] (sink (source)))
;; ruleid: flow
(if-let [x ""] (sink (source)))
;; ruleid: flow
(if-let [x []] (sink (source)))
;; ruleid: flow
(if-some [x true] (sink (source)))
;; ruleid: flow
(if-some [x false] (sink (source)))
(if-some [x nil] (sink (source)))
;; ruleid: flow
(if-some [x 0] (sink (source)))
;; ruleid: flow
(if-some [x ""] (sink (source)))
;; ruleid: flow
(if-some [x []] (sink (source)))

(when-first [x []] (sink (source)))
(when-first [x nil] (sink (source)))
;; ruleid: flow
(when-first [x [(source) "safe"]] (sink x))
(when-first [x ["safe" (source)]] (sink x))
;; ruleid: flow
(when-first [[x] [[(source)]]] (sink x))
;; ruleid: flow
(if-let [x nil] nil (sink (source)))
;; ruleid: flow
(if-some [x nil] nil (sink (source)))
(if-let [x true] nil (sink (source)))
(if-some [x false] nil (sink (source)))
;; ruleid: flow
(let [value (if-not false (source) "safe")] (sink value))
(let [value (if-not true (source) "safe")] (sink value))
;; ruleid: flow
(let [value (if-let [x true] (source) "safe")] (sink value))
(let [value (if-let [x false] (source) "safe")] (sink value))
;; ruleid: flow
(let [value (if-some [x false] (source) "safe")] (sink value))
(let [value (if-some [x nil] (source) "safe")] (sink value))
;; ruleid: flow
(when-let [x (source)] (sink x))
;; ruleid: flow
(when-some [{:keys [x]} {:x (source)}] (sink x))
;; ruleid: flow
(if-let [[x] [(source)]] (sink x))

(let [x (source)]
  (when-let [x "safe"] (sink x))
  ;; ruleid: flow
  (sink x))
(let [x "safe"]
  (when-let [x (source)] nil)
  (sink x))
(let [x (source)]
  (when-some [x "safe"] (sink x))
  ;; ruleid: flow
  (sink x))
(let [x "safe"]
  (when-first [x [(source)]] nil)
  (sink x))
(when-let [x (do
              ;; ruleid: flow
              (sink (source))
              nil)]
  (sink (source)))
(if-let [x (do
            ;; ruleid: flow
            (sink (source))
            false)]
  (sink (source))
  "safe")
(if-let [x true] nil (sink (source)))
;; ruleid: flow
(if-let [x false] nil (sink (source)))
;; ruleid: flow
(if-let [x nil] nil (sink (source)))
(if-let [x 0] nil (sink (source)))
(if-let [x ""] nil (sink (source)))
(if-let [x []] nil (sink (source)))
(if-let [x {}] nil (sink (source)))
(if-let [x :ready] nil (sink (source)))
(if-some [x true] nil (sink (source)))
(if-some [x false] nil (sink (source)))
;; ruleid: flow
(if-some [x nil] nil (sink (source)))
(if-some [x 0] nil (sink (source)))
(if-some [x ""] nil (sink (source)))
(if-some [x []] nil (sink (source)))
(if-some [x {}] nil (sink (source)))
(if-some [x :ready] nil (sink (source)))
(when-first [x ""] (sink (source)))
(when-first [x ()] (sink (source)))
(when-let [{:keys [missing]} {}] (sink missing))
;; ruleid: flow
(when-let [{:keys [missing]} {}] (sink (source)))

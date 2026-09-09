(sink {:root "/srv/public" ":root" (source)})
(sink {":root" (source) :root "/srv/public"})
;; ruleid: flow
(sink {:root (source) ":root" "/srv/public"})
;; ruleid: flow
(sink {":root" "/srv/public" :root (source)})

(let [options {:root "/srv/public" ":root" (source)}]
  (sink options)
  (sink (assoc options ":root" (source))))
(let [options {:root (source) ":root" "/srv/public"}]
  ;; ruleid: flow
  (sink (assoc options ":root" "other")))
(let [key :root options {key (source)}]
  ;; ruleid: flow
  (sink options))
(let [key ":root" options {key (source) :root "/srv/public"}]
  (sink options))

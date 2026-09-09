class Service
  def initialize(value)
    sink(value)
  end
end
Service.unrelated(source())

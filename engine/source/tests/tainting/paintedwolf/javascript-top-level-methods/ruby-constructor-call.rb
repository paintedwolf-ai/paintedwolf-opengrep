class Service
  def initialize(value)
    # ruleid: method-flow
    sink(value)
  end
end
Service.new(source())

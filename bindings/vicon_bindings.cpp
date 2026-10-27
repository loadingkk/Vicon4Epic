#include <pybind11/pybind11.h>
#include <pybind11/eigen.h>
#include "vicon.hpp"
#include <chrono>
#include <thread>
#include <exception>

namespace py = pybind11;

PYBIND11_MODULE(vicon_tracker, m) {
    m.doc() = "Python bindings for the vicon class";
    m.attr("__version__") = "1.0";

    py::class_<vicon>(m, "vicon")
        .def(py::init<>())
        .def("open", (void (vicon::*)(std::string)) &vicon::open, py::arg("object"))
        .def("open", (void (vicon::*)()) &vicon::open)
        .def("close", &vicon::close)
        .def("listen", [](vicon& self, py::function callback) {
            if (!self.on) throw std::runtime_error("Call open() before listen()");
            std::exception_ptr error;
            self.pose_handler = [&](const Eigen::Vector3d& position,
                                    const Eigen::Matrix3d& rotation,
                                    double timestamp, int sensor) {
                if (error) return;
                try {
                    callback(py::cast(position, py::return_value_policy::copy),
                             py::cast(rotation, py::return_value_policy::copy),
                             timestamp, sensor);
                } catch (...) { error = std::current_exception(); }
            };
            try {
                while (self.on) {
                    if (PyErr_CheckSignals() != 0) throw py::error_already_set();
                    self.loop();
                    if (error) std::rethrow_exception(error);
                    // Pump VRPN frequently; output happens only inside its data callback.
                    { py::gil_scoped_release release;
                      std::this_thread::sleep_for(std::chrono::microseconds(100)); }
                }
            } catch (...) {
                self.pose_handler = nullptr;
                throw;
            }
            self.pose_handler = nullptr;
        }, py::arg("callback"))
        .def("loop", [](vicon& self) {
            auto [x_v, R_vm] = self.loop();
            return std::make_pair(x_v, R_vm);  // Automatically converted to NumPy arrays
        });
}

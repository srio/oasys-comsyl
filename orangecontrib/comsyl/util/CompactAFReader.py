import h5py
import numpy as np

from comsyl.autocorrelation.AutocorrelationFunction import AutocorrelationFunction, AutocorrelationFunctionIO
from comsyl.autocorrelation.SigmaMatrix import SigmaMatrix
from comsyl.autocorrelation.AutocorrelationInfo import AutocorrelationInfo
from comsyl.math.Twoform import Twoform
from comsyl.waveoptics.Wavefront import NumpyWavefront
from comsyl.autocorrelation.AutocorrelationFunctionIO import undulator_from_numpy_array
from comsyl.math.TwoformVectors import TwoformVectorsEigenvectors


class CompactAFReader(object):
    def __init__(self, af=None, data_dict=None, filename=None, h5f=None):
        self._af   = af
        self._data_dict = data_dict
        self._filename = filename
        self._h5f = h5f

    def __del__(self):
        self.close_h5_file()

    @classmethod
    def initialize_from_h5_file(cls,filename):
        # data_dict = AutocorrelationFunctionIO.loadh5(filename)
        data_dict, h5f = cls.loadh5_to_dictionaire(filename)
        # af = AutocorrelationFunction.fromDictionary(data_dict)
        af = cls.fromDictionary(data_dict)
        return CompactAFReader(af,data_dict,filename,h5f)


    @classmethod
    def initialize_from_file(cls,filename):
        filename_extension = filename.split('.')[-1]
        try:
            if filename_extension == "h5":
                return cls.initialize_from_h5_file(filename)
            elif filename_extension == "npz":
                data_dict = AutocorrelationFunctionIO.load(filename)
                af = AutocorrelationFunction.fromDictionary(data_dict)
                af._io._setWasFileLoaded(filename)
                return CompactAFReader(af,data_dict,filename)
            # elif filename_extension == "npy":
            #     filename_without_extension = ('.').join(filename.split('.')[:-1])
            #     return CompactAFReader(AutocorrelationFunction.load(filename_without_extension+".npz"))
            else:
                raise FileExistsError("Please enter a file with .npy, .npz or .h5 extension")
        except:
            raise FileExistsError("Error reading file")



    @classmethod
    def loadh5_to_dictionaire(cls,filename):
        try:
            h5f = h5py.File(filename,'r')
        except:
            raise Exception("Failed to read h5 file: %s"%filename)

        data_dict = dict()

        for key in h5f.keys():
            if (key !="twoform_4"):
                data_dict[key] = h5f[key].value
            else:
                data_dict[key] = h5f[key] # TwoformVectorsEigenvectors(h5f[key])
        # IMPORTANT: DO NOT CLOSE FILE
        # h5f.close()
        return data_dict, h5f

    @staticmethod
    def fromDictionary(data_dict):

        sigma_matrix = SigmaMatrix.fromNumpyArray(data_dict["sigma_matrix"])
        undulator = undulator_from_numpy_array(data_dict["undulator"])
        detuning_parameter = data_dict["detuning_parameter"][0]
        energy = data_dict["energy"][0]

        electron_beam_energy = data_dict["electron_beam_energy"][0]


        np_wavefront_0=data_dict["wavefront_0"]
        np_wavefront_1=data_dict["wavefront_1"]
        np_wavefront_2=data_dict["wavefront_2"]
        wavefront = NumpyWavefront.fromNumpyArray(np_wavefront_0, np_wavefront_1, np_wavefront_2)

        try:
            np_exit_slit_wavefront_0=data_dict["exit_slit_wavefront_0"]
            np_exit_slit_wavefront_1=data_dict["exit_slit_wavefront_1"]
            np_exit_slit_wavefront_2=data_dict["exit_slit_wavefront_2"]
            exit_slit_wavefront = NumpyWavefront.fromNumpyArray(np_exit_slit_wavefront_0, np_exit_slit_wavefront_1, np_exit_slit_wavefront_2)
        except:
            exit_slit_wavefront = wavefront.clone()

        try:
            weighted_fields = data_dict["weighted_fields"]
        except:
            weighted_fields = None



        srw_wavefront_rx=data_dict["srw_wavefront_rx"][0]
        srw_wavefront_ry=data_dict["srw_wavefront_ry"][0]

        srw_wavefront_drx = data_dict["srw_wavefront_drx"][0]
        srw_wavefront_dry = data_dict["srw_wavefront_dry"][0]

        info_string = str(data_dict["info"])
        info = AutocorrelationInfo.fromString(info_string)


        sampling_factor=data_dict["sampling_factor"][0]
        minimal_size=data_dict["minimal_size"][0]

        beam_energies = data_dict["beam_energies"]

        static_electron_density = data_dict["static_electron_density"]
        coordinates_x = data_dict["twoform_0"]
        coordinates_y = data_dict["twoform_1"]
        diagonal_elements = data_dict["twoform_2"]
        eigenvalues = data_dict["twoform_3"]

        # do not read the big array with modes
        twoform_vectors = None # data_dict["twoform_4"]

        twoform = Twoform(coordinates_x, coordinates_y, diagonal_elements, eigenvalues, twoform_vectors)

        eigenvector_errors = data_dict["twoform_5"]

        twoform.setEigenvectorErrors(eigenvector_errors)

        af = AutocorrelationFunction(sigma_matrix, undulator, detuning_parameter,energy,electron_beam_energy,
                                     wavefront,exit_slit_wavefront,srw_wavefront_rx, srw_wavefront_drx, srw_wavefront_ry, srw_wavefront_dry,
                                     sampling_factor,minimal_size, beam_energies, weighted_fields,
                                     static_electron_density, twoform,
                                     info)

        af._x_coordinates = coordinates_x
        af._y_coordinates = coordinates_y

        af._intensity = diagonal_elements.reshape(len(coordinates_x), len(coordinates_y))

        return af


    def close_h5_file(self):
        try:
            self._h5f.close()
        except:
            pass

    def eigenvalues(self):
        return self._af.eigenvalues()

    def eigenvalue(self,mode):
        return self._af.eigenvalue(mode)

    def x_coordinates(self):
        return self._af.xCoordinates()

    def y_coordinates(self):
        return self._af.yCoordinates()

    def spectral_density(self):
        return self._af.intensity()

    def reference_electron_density(self):
        return self._af.staticElectronDensity()

    def reference_undulator_radiation(self):
        return self._af.referenceWavefront().intensity_as_numpy()

    def photon_energy(self):
        return self._af.photonEnergy()

    def total_intensity_from_spectral_density(self):
        return self.spectral_density().real.sum()

    def total_intensity(self):
        return (np.absolute(self._af.intensity())).sum()

    def occupation_array(self):
        return self._af.modeDistribution()

    def occupation(self, i_mode):
        return self.occupation_array()[i_mode]

    def occupation_all_modes(self):
        return self.occupation_array().real.sum()


    def mode(self, i_mode):
        p = self._data_dict["twoform_4"]
        if isinstance(p,h5py._hl.dataset.Dataset):
            try:
                return p[i_mode,:,:]
            except:
                raise Exception("Problem accessing data in h5 file: %s"%self._filename)
        elif isinstance(p,TwoformVectorsEigenvectors):
            try:
                return self._af.Twoform().vector(i_mode) #AllVectors[i_mode,:,:]
            except:
                raise Exception("Problem accessing data in numpy file: %s"%self._filename)
        else:
            raise Exception("Unknown format for mode stokage.")

    def number_modes(self):
        return self.eigenvalues().size

    @property
    def shape(self):
        return (self.number_modes(), self.x_coordinates().size, self.y_coordinates().size)

    def total_intensity_from_modes(self):
        intensity = np.zeros_like(self.mode(0))

        for i_e, eigenvalue in enumerate(self.eigenvalues()):
            intensity += eigenvalue * (np.abs(self.mode(i_e))**2)
        return np.abs(intensity).sum()

    def keys(self):
        return self._data_dict.keys()

    def info(self,list_modes=True):
        txt = "contains\n"


        txt += "Occupation and max abs value of the mode\n"
        percent = 0.0
        if list_modes:
            for i_mode in range(self.number_modes()):
                occupation = np.abs(self.occupation(i_mode))
                percent += occupation
                txt += "%i occupation: %e, accumulated percent: %12.10f\n" % (i_mode, occupation, 100*percent)


        txt += "%i modes\n" % self.number_modes()
        txt += "on the grid\n"
        txt += "x: from %e to %e\n" % (self.x_coordinates().min(), self.x_coordinates().max())
        txt += "y: from %e to %e\n" % (self.y_coordinates().min(), self.y_coordinates().max())
        txt += "calculated at %f eV\n" % self.photon_energy()
        txt += "total intensity from spectral density with (maybe improper) normalization: %e\n" % self.total_intensity_from_spectral_density()
        txt += "total intensity: %g\n"%self.total_intensity()
        txt += "total intensity from modes: %g\n"%self.total_intensity_from_modes()
        txt += "Occupation of all modes: %g\n"%self.occupation_all_modes()
        txt += ">> Shape x,y, (%d,%d)\n"%(self.x_coordinates().size,self.y_coordinates().size)
        txt += ">> Shape Spectral density "+repr(self.spectral_density().shape)+"\n"
        txt += ">> Shape Photon Energy "+repr(self.photon_energy().shape)+"\n"
        txt += "Modes index to 90 percent occupancy: %d\n"%self.mode_up_to_percent(90.0)
        txt += "Modes index to 95 percent occupancy: %d\n"%self.mode_up_to_percent(95.0)
        txt += "Modes index to 99 percent occupancy: %d\n"%self.mode_up_to_percent(99.0)

        # print(">> Shape modes",self.modes().shape)
        # print(">> Shape modes  %d bytes, %6.2f Gigabytes: "%(self.modes().nbytes,self.modes().nbytes/(1024**3)))

        return txt

    def mode_up_to_percent(self,up_to_percent):

        perunit = 0.0
        for i_mode in range(self.number_modes()):
            occupation = self.occupation(i_mode)
            perunit += occupation
            if 100*perunit >= up_to_percent:
                return i_mode

        print("The modes in the file contain %4.2f (less than %4.2f) occupancy"%(100*perunit,up_to_percent))
        return -1

#
# auxiliary functions
#
def test_equal(af1,af2):
        np.testing.assert_almost_equal(af1.eigenvalue(5),af2.eigenvalue(5))
        np.testing.assert_almost_equal(af1.eigenvalue(5),af2.eigenvalue(5))
        np.testing.assert_almost_equal(af1.photon_energy(),af2.photon_energy())
        np.testing.assert_almost_equal(af1.total_intensity_from_spectral_density(),af2.total_intensity_from_spectral_density())
        np.testing.assert_almost_equal(af1.total_intensity(),af2.total_intensity())
        np.testing.assert_almost_equal(af1.number_modes(),af2.number_modes())
        np.testing.assert_almost_equal(af1.eigenvalues(), af2.eigenvalues())
        np.testing.assert_almost_equal(af1.x_coordinates(), af2.x_coordinates())
        np.testing.assert_almost_equal(af1.y_coordinates(), af2.y_coordinates())
        np.testing.assert_almost_equal(af1.spectral_density(), af2.spectral_density())
        np.testing.assert_almost_equal(af1.reference_electron_density(), af2.reference_electron_density())
        np.testing.assert_almost_equal(af1.reference_undulator_radiation(), af2.reference_undulator_radiation())
        np.testing.assert_almost_equal(af1.mode(25), af2.mode(25))
        np.testing.assert_almost_equal(af1.shape, af2.shape)

        np.testing.assert_almost_equal(af1.total_intensity_from_modes(),af2.total_intensity_from_modes()) #SLOW

def print_scattered_info(af1,af2=None):
        if af2 is None:
            af2 = af1

        print("File is: ",af1._filename,af2._filename)
        print("Eigenvalue 5: ",af1.eigenvalue(5),af2.eigenvalue(5))
        print("photon_energy : ",af1.photon_energy(),af2.photon_energy())
        print("total_intensity_from_spectral_density : ",af1.total_intensity_from_spectral_density(),af2.total_intensity_from_spectral_density())
        print("total_intensity : ",af1.total_intensity(),af2.total_intensity())
        print("number_modes : ",af1.number_modes(),af2.number_modes())

        print("Eigenvalues shape: ",                  af1.eigenvalues().shape, af2.eigenvalues().shape)
        print("x_coordinates shape: ",                af1.x_coordinates().shape, af2.x_coordinates().shape)
        print("y_coordinates shape: ",                af1.y_coordinates().shape, af2.y_coordinates().shape)
        print("spectral_density shape: ",             af1.spectral_density().shape, af2.spectral_density().shape)
        print("reference_electron_density shape: ",   af1.reference_electron_density().shape, af2.reference_electron_density().shape)
        print("reference_undulator_radiation shape: ",af1.reference_undulator_radiation().shape, af2.reference_undulator_radiation().shape)
        print("mode 25 shape: ",                      af1.mode(25).shape, af2.mode(25).shape)
        print("shape : ",                             af1.shape, af2.shape)

        print("keys : ",af1.keys(),af2.keys())
        print("total_intensity_from_modes [SLOW]: ",af1.total_intensity_from_modes(),af2.total_intensity_from_modes())

        af1.close_h5_file()
        af2.close_h5_file()
        # print("mode 25 shape: ",af2.mode(25).shape)  # should fail after closing









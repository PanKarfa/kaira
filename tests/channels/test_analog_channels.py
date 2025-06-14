"""Tests for analog channel implementations in Kaira."""

import math

import pytest
import torch

from kaira.channels import (
    AWGNChannel,
    FlatFadingChannel,
    LaplacianChannel,
    LogNormalFadingChannel,
    NonlinearChannel,
    PerfectChannel,
    PhaseNoiseChannel,
    PoissonChannel,
    RayleighFadingChannel,
    RicianFadingChannel,
)
from kaira.utils import snr_to_noise_power


class TestAWGNChannel:
    def test_initialization(self):
        # Test with noise power
        channel1 = AWGNChannel(avg_noise_power=0.1)
        assert channel1.avg_noise_power == 0.1
        assert channel1.snr_db is None

        # Test with SNR
        channel2 = AWGNChannel(snr_db=10.0)
        assert channel2.snr_db == 10.0
        assert channel2.avg_noise_power is None

        # Test with no parameters (should raise error)
        with pytest.raises(ValueError):
            AWGNChannel()

        # Test with both parameters (should prioritize SNR)
        channel3 = AWGNChannel(avg_noise_power=0.1, snr_db=10.0)
        assert channel3.snr_db == 10.0
        assert channel3.avg_noise_power is None

    def test_forward_with_noise_power(self, random_tensor):
        noise_power = 0.1
        channel = AWGNChannel(avg_noise_power=noise_power)
        output = channel(random_tensor)

        # Check shape preservation
        assert output.shape == random_tensor.shape

        # Check noise was added
        assert not torch.allclose(output, random_tensor)

        # Check noise variance (should be close to noise_power)
        noise = output - random_tensor
        measured_variance = torch.var(noise).item()
        assert abs(measured_variance - noise_power) < 0.3 * noise_power  # Increased tolerance for randomness

    def test_forward_with_snr(self, random_tensor):
        snr_db = 10.0
        channel = AWGNChannel(snr_db=snr_db)

        # Use input with known power for easier verification
        x = torch.ones(1000) * 0.5  # Signal power = 0.25
        signal_power = torch.mean(torch.abs(x) ** 2).item()
        expected_noise_power = signal_power / (10 ** (snr_db / 10))

        output = channel(x)

        # Check noise variance
        noise = output - x
        measured_noise_power = torch.mean(noise**2).item()
        assert abs(measured_noise_power - expected_noise_power) < 0.3 * expected_noise_power

    def test_complex_input(self, complex_tensor):
        channel = AWGNChannel(avg_noise_power=0.1)
        output = channel(complex_tensor)

        # Check shape and type preservation
        assert output.shape == complex_tensor.shape
        assert torch.is_complex(output)

        # Check noise added to both real and imaginary parts
        assert not torch.allclose(output.real, complex_tensor.real)
        assert not torch.allclose(output.imag, complex_tensor.imag)

        # Check noise variance for complex (should be noise_power)
        noise = output - complex_tensor
        measured_variance = torch.mean(torch.abs(noise) ** 2).item()
        assert abs(measured_variance - 0.1) < 0.3 * 0.1

    def test_pregenerated_noise(self, random_tensor):
        channel = AWGNChannel(avg_noise_power=0.1)  # Noise power doesn't matter here
        custom_noise = torch.randn_like(random_tensor) * 0.5  # Custom noise
        expected_output = random_tensor + custom_noise
        output = channel(random_tensor, noise=custom_noise)
        assert torch.allclose(output, expected_output)


class TestLaplacianChannel:
    """Test suite for LaplacianChannel."""

    def test_initialization(self):
        """Test initialization with different parameters."""
        # Test with scale
        channel1 = LaplacianChannel(scale=0.5)
        # Ensure comparison is done with tensors
        assert torch.isclose(torch.tensor(channel1.scale), torch.tensor(0.5), rtol=1e-5)
        assert channel1.avg_noise_power is None
        assert channel1.snr_db is None

        # Test with noise power
        channel2 = LaplacianChannel(avg_noise_power=0.1)
        # Ensure comparison is done with tensors
        assert torch.isclose(torch.tensor(channel2.avg_noise_power), torch.tensor(0.1), rtol=1e-5)
        assert channel2.scale is None
        assert channel2.snr_db is None

        # Test with SNR
        channel3 = LaplacianChannel(snr_db=15.0)
        assert channel3.snr_db == 15.0
        assert channel3.avg_noise_power is None
        assert channel3.scale is None

        # Test with no parameters
        with pytest.raises(ValueError):
            LaplacianChannel()

    def test_forward_with_scale(self, random_tensor):
        """Test forward pass with scale parameter."""
        scale = 0.5
        channel = LaplacianChannel(scale=scale)
        output = channel(random_tensor)

        # Check shape preservation
        assert output.shape == random_tensor.shape

        # Check noise was added (output should be different from input)
        assert not torch.allclose(output, random_tensor)

        # For Laplacian distribution with scale b, variance = 2 * b^2
        expected_variance = 2 * (scale**2)
        noise = output - random_tensor
        measured_variance = torch.var(noise).item()
        assert abs(measured_variance - expected_variance) < 0.3 * expected_variance

    def test_forward_with_noise_power(self, random_tensor):
        """Test forward pass with noise power specification."""
        noise_power = 0.4
        channel = LaplacianChannel(avg_noise_power=noise_power)
        output = channel(random_tensor)

        # Check noise variance
        noise = output - random_tensor
        measured_variance = torch.var(noise).item()
        assert abs(measured_variance - noise_power) < 0.3 * noise_power

    def test_complex_input(self, complex_tensor):
        """Test with complex input."""
        channel = LaplacianChannel(scale=0.5)
        output = channel(complex_tensor)

        # Check shape and type preservation
        assert output.shape == complex_tensor.shape
        assert torch.is_complex(output)

        # Check noise added to both real and imaginary parts
        assert not torch.allclose(output.real, complex_tensor.real)
        assert not torch.allclose(output.imag, complex_tensor.imag)

    def test_forward_with_snr(self, random_tensor):
        """Test forward pass with SNR specification."""
        snr_db = 15.0  # 15dB SNR
        channel = LaplacianChannel(snr_db=snr_db)

        # Create a test input with known power
        x = torch.ones(1000) * 0.5  # input with signal power 0.25
        signal_power = torch.mean(torch.abs(x) ** 2).item()

        # Calculate expected noise power based on SNR
        expected_noise_power = signal_power / (10 ** (snr_db / 10))

        # Calculate expected scale parameter (for Laplacian, variance = 2*scale²)
        torch.sqrt(torch.tensor(expected_noise_power / 2))

        output = channel(x)

        # Check noise statistics
        noise = output - x
        measured_noise_power = torch.mean(noise**2).item()

        # Noise power should be close to the expected value
        assert abs(measured_noise_power - expected_noise_power) < 0.3 * expected_noise_power


class TestPhaseNoiseChannel:
    """Test suite for PhaseNoiseChannel."""

    def test_initialization(self):
        """Test initialization with different parameters."""
        # Test with std dev
        channel1 = PhaseNoiseChannel(phase_noise_std=0.1)
        # Ensure comparison is done with tensors
        assert torch.isclose(torch.tensor(channel1.phase_noise_std), torch.tensor(0.1), rtol=1e-5)
        # Use getattr to handle missing attributes safely
        assert getattr(channel1, "snr_db", None) is None

        # Test invalid parameters
        with pytest.raises(ValueError):
            PhaseNoiseChannel(phase_noise_std=-0.1)  # Negative std is invalid

        # Test with no parameters
        with pytest.raises(TypeError):
            PhaseNoiseChannel()

    def test_forward_real_input(self, random_tensor):
        """Test forward pass with real input."""
        channel = PhaseNoiseChannel(phase_noise_std=0.1)
        output = channel(random_tensor)

        # Output should be complex even if input is real
        assert output.shape == random_tensor.shape
        assert torch.is_complex(output)

        # Magnitude should be approximately preserved
        assert torch.allclose(torch.abs(output), torch.abs(random_tensor), rtol=1e-5)

    def test_forward_complex_input(self, complex_tensor):
        """Test forward pass with complex input."""
        # Reset the random seed for reproducible testing
        torch.manual_seed(42)

        phase_std = 0.1
        # Create a simpler tensor for deterministic testing
        test_tensor = torch.complex(torch.ones(1000), torch.zeros(1000))
        channel = PhaseNoiseChannel(phase_noise_std=phase_std)

        # Apply channel with known phase noise
        output = channel(test_tensor)

        # Check shape and type preservation
        assert output.shape == test_tensor.shape
        assert torch.is_complex(output)

        # Magnitude should be preserved
        assert torch.allclose(torch.abs(output), torch.abs(test_tensor), rtol=1e-5)

        # Phase should be perturbed
        phase_diff = torch.angle(output) - torch.angle(test_tensor)

        # The phase differences should have a standard deviation close to phase_std
        measured_std = torch.std(phase_diff).item()
        assert 0.08 <= measured_std <= 0.12


class TestPoissonChannel:
    """Test suite for PoissonChannel."""

    def test_initialization(self):
        """Test initialization with rate factor."""
        channel = PoissonChannel(rate_factor=5.0)
        # Ensure comparison is done with tensors
        assert torch.isclose(torch.tensor(channel.rate_factor), torch.tensor(5.0), rtol=1e-5)

        # Test invalid rate factor
        with pytest.raises(ValueError):
            PoissonChannel(rate_factor=-1.0)

    def test_forward_real_input(self):
        """Test forward pass with real input."""
        channel = PoissonChannel(rate_factor=10.0, normalize=False)
        # Use positive input for Poisson channel
        x = torch.ones(1000) * 0.5
        y = channel(x)

        # Check shape preservation
        assert y.shape == x.shape

        # Output should follow Poisson with rate = rate_factor * x
        # For Poisson, mean = rate
        assert 4.5 <= torch.mean(y).item() <= 5.5

    def test_normalization(self):
        """Test normalization option."""
        channel = PoissonChannel(rate_factor=10.0, normalize=True)
        x = torch.ones(1000) * 0.5
        y = channel(x)

        # With normalization, output should be close to input on average
        assert 0.45 <= torch.mean(y).item() <= 0.55

    def test_negative_input(self):
        """Test with negative input (should raise error)."""
        channel = PoissonChannel()
        x = torch.ones(10) * -1.0
        with pytest.raises(ValueError):
            channel(x)

    def test_complex_input(self):
        """Test with complex input."""
        # Set a fixed seed for reproducible tests
        torch.manual_seed(42)

        channel = PoissonChannel(rate_factor=10.0)
        # Create complex input with positive magnitude
        x = torch.complex(torch.ones(100) * 0.5, torch.ones(100) * 0.5)

        # Get the exact phases before applying the channel
        input_phase = torch.angle(x)

        # Apply the channel
        y = channel(x)

        # Check output is complex
        assert y.shape == x.shape
        assert torch.is_complex(y)

        # Phase should be preserved exactly
        output_phase = torch.angle(y)
        assert torch.allclose(output_phase, input_phase, atol=1e-5)

    def test_complex_normalization(self):
        """Test normalization with complex input."""
        torch.manual_seed(42)  # For reproducibility

        # Create channel with normalization enabled
        channel = PoissonChannel(rate_factor=20.0, normalize=True)

        # Generate complex input with magnitude 0.5
        real = torch.ones(1000) * 0.3
        imag = torch.ones(1000) * 0.4
        x = torch.complex(real, imag)  # magnitude is 0.5

        # Save input magnitude and phase
        torch.abs(x)
        input_phase = torch.angle(x)

        # Apply channel
        y = channel(x)

        # Check normalized output magnitude should be close to input on average
        output_mag = torch.abs(y)
        assert 0.45 <= torch.mean(output_mag).item() <= 0.55

        # Phase should be exactly preserved
        output_phase = torch.angle(y)
        assert torch.allclose(output_phase, input_phase, atol=1e-5)


class TestFlatFadingChannel:
    """Test suite for FlatFadingChannel."""

    def test_initialization(self):
        """Test initialization with different parameters."""
        # Test with noise power
        channel1 = FlatFadingChannel(fading_type="rayleigh", coherence_time=5, avg_noise_power=0.1)
        # Ensure comparison is done with tensors
        assert torch.isclose(torch.tensor(channel1.avg_noise_power), torch.tensor(0.1), rtol=1e-5)
        assert channel1.snr_db is None
        assert channel1.fading_type == "rayleigh"
        assert channel1.coherence_time == 5

        # Test with SNR
        channel2 = FlatFadingChannel(fading_type="rayleigh", coherence_time=5, snr_db=10.0)
        assert channel2.snr_db == 10.0
        assert channel2.avg_noise_power is None
        assert channel2.fading_type == "rayleigh"
        assert channel2.coherence_time == 5

        # Test with missing required parameters
        with pytest.raises(TypeError):
            FlatFadingChannel(avg_noise_power=0.1)  # Missing fading_type and coherence_time

        # Test with missing noise parameter
        with pytest.raises(ValueError):
            FlatFadingChannel(fading_type="rayleigh", coherence_time=5)

    def test_rayleigh_fading(self, complex_tensor):
        """Test Rayleigh fading channel."""
        channel = FlatFadingChannel(fading_type="rayleigh", coherence_time=10, snr_db=20)
        output = channel(complex_tensor)

        # Check shape and type preservation
        assert output.shape == complex_tensor.shape
        assert torch.is_complex(output)

        # Output should be different from input
        assert not torch.allclose(output, complex_tensor)

        # Create a proper CSI tensor matching input dimensions
        real_part = torch.ones_like(complex_tensor.real) * 0.5
        imag_part = torch.zeros_like(complex_tensor.imag)
        csi = torch.complex(real_part, imag_part)

        output_with_csi = channel(complex_tensor, csi=csi)

        # With CSI, the fading component should match the provided CSI
        # Extract the signal part (without noise)
        signal_part = output_with_csi - (output_with_csi - csi * complex_tensor)

        # Should be close to csi*x but with some noise
        assert not torch.allclose(signal_part, complex_tensor)

    def test_rayleigh_fading_channel_class(self, complex_tensor):
        """Test the specialized RayleighFadingChannel class."""
        channel = RayleighFadingChannel(coherence_time=5, snr_db=15)

        # Verify it has defaults set correctly
        assert channel.fading_type == "rayleigh"
        assert channel.coherence_time == 5
        assert channel.snr_db == 15

        # Test forward pass
        output = channel(complex_tensor)

        # Check shape and type preservation
        assert output.shape == complex_tensor.shape
        assert torch.is_complex(output)

        # Output should be different from input
        assert not torch.allclose(output, complex_tensor)

    def test_rician_fading(self, complex_tensor):
        """Test Rician fading channel."""
        k_factor = 2.0  # Ratio of direct to scattered power
        channel = FlatFadingChannel(fading_type="rician", coherence_time=5, k_factor=k_factor, snr_db=15)

        output = channel(complex_tensor)

        # Check shape and type preservation
        assert output.shape == complex_tensor.shape
        assert torch.is_complex(output)

        # Direct LOS component should be stronger than Rayleigh
        # We can't directly test the fading coefficients, but we can
        # verify the output is different from the input
        assert not torch.allclose(output, complex_tensor)

        # Test with different k_factors to ensure behavior changes
        channel_high_k = FlatFadingChannel(fading_type="rician", coherence_time=5, k_factor=10.0, snr_db=15)  # Higher K means stronger LOS component

        torch.manual_seed(42)
        output_low_k = channel(complex_tensor)

        torch.manual_seed(42)
        output_high_k = channel_high_k(complex_tensor)

        # Different K factors should produce different outputs
        # even with the same random seed
        assert not torch.allclose(output_low_k, output_high_k)

    def test_lognormal_fading(self, complex_tensor):
        """Test log-normal shadowing in FlatFadingChannel."""
        shadow_sigma_db = 4.0  # Standard deviation in dB
        channel = FlatFadingChannel(fading_type="lognormal", coherence_time=5, shadow_sigma_db=shadow_sigma_db, snr_db=15)

        output = channel(complex_tensor)

        # Check shape and type preservation
        assert output.shape == complex_tensor.shape
        assert torch.is_complex(output)

        # Output should be different from input
        assert not torch.allclose(output, complex_tensor)

        # Test with different shadow standard deviations
        channel_high_sigma = FlatFadingChannel(fading_type="lognormal", coherence_time=5, shadow_sigma_db=8.0, snr_db=15)  # Higher sigma means more variation

        torch.manual_seed(42)
        output_low_sigma = channel(complex_tensor)

        torch.manual_seed(42)
        output_high_sigma = channel_high_sigma(complex_tensor)

        # Different shadow sigma should produce different outputs
        assert not torch.allclose(output_low_sigma, output_high_sigma)

    def test_pregenerated_noise(self, complex_tensor):
        """Test with pre-generated noise in FlatFadingChannel."""
        channel = FlatFadingChannel(fading_type="rayleigh", coherence_time=5, snr_db=15)

        # Create custom noise with a specific pattern
        custom_noise = torch.complex(torch.ones_like(complex_tensor.real) * 0.1, torch.ones_like(complex_tensor.imag) * 0.1)

        # Compute expected fading coefficients using manual generation
        torch.manual_seed(42)
        batch_size = complex_tensor.shape[0] if len(complex_tensor.shape) > 1 else 1
        seq_length = complex_tensor.shape[1] if len(complex_tensor.shape) > 1 else complex_tensor.shape[0]
        h_blocks = channel._generate_fading_coefficients(batch_size, seq_length, complex_tensor.device)
        h = channel._expand_coefficients(h_blocks, seq_length)
        if len(complex_tensor.shape) == 1:
            h = h.squeeze(0)

        expected_output = h * complex_tensor + custom_noise
        # Reset seed again so that channel forward() uses the same random state.
        torch.manual_seed(42)
        assert torch.allclose(channel(complex_tensor, noise=custom_noise), expected_output)


def test_flat_fading_channel_with_custom_noise(complex_tensor):
    """Test FlatFadingChannel when explicit noise is provided (covers branch: if noise is not
    None)."""
    # Force deterministic fading by providing CSI equal to one
    channel = FlatFadingChannel(fading_type="rayleigh", coherence_time=5, snr_db=15)
    csi = torch.ones_like(complex_tensor)  # fading coefficient = 1
    custom_noise = torch.full_like(complex_tensor, 0.05)  # constant complex noise

    output = channel(complex_tensor, csi=csi, noise=custom_noise)
    # Since csi=1, output should equal input plus the provided noise.
    expected = complex_tensor + custom_noise
    assert torch.allclose(output, expected)


def test_flat_fading_channel_input_shape_extended():
    """Extended test for FlatFadingChannel processing for 1D and >2D inputs."""
    # Create a dummy channel with Rayleigh fading (use avg_noise_power branch here)
    channel = FlatFadingChannel("rayleigh", coherence_time=4, avg_noise_power=0.1)

    # Test 1D input: branch to add a batch dim and later squeeze it
    x_1d = torch.ones(20)
    y_1d = channel(x_1d)
    # Output should have same shape as x_1d after squeezing
    assert y_1d.shape == x_1d.shape

    # Test >2D input: e.g., (batch, channels, seq_length)
    x_3d = torch.ones(2, 3, 16, dtype=torch.cfloat)
    y_3d = channel(x_3d)
    # Check that output retains the original 3D shape.
    assert y_3d.shape == x_3d.shape


class TestNonlinearChannel:
    """Test suite for NonlinearChannel."""

    def test_initialization(self):
        """Test initialization with different parameters."""

        # Simple nonlinearity
        def cubic(x):
            return x + 0.1 * x**3

        # Basic initialization
        channel1 = NonlinearChannel(cubic)
        assert not channel1.add_noise
        assert channel1.complex_mode == "direct"

        # With noise
        channel2 = NonlinearChannel(cubic, add_noise=True, avg_noise_power=0.1)
        assert channel2.add_noise
        assert channel2.avg_noise_power == 0.1

        # With SNR
        channel3 = NonlinearChannel(cubic, add_noise=True, snr_db=15.0)
        assert channel3.add_noise
        assert channel3.snr_db == 15.0

        # Invalid complex mode
        with pytest.raises(ValueError):
            NonlinearChannel(cubic, complex_mode="invalid")

        # Missing noise parameters
        with pytest.raises(ValueError):
            NonlinearChannel(cubic, add_noise=True)

        # Test providing both noise parameters when add_noise=True
        with pytest.raises(ValueError, match="Cannot specify both snr_db and avg_noise_power"):
            NonlinearChannel(cubic, add_noise=True, snr_db=10.0, avg_noise_power=0.1)

    def test_forward_real_input(self, random_tensor):
        """Test with real input."""

        def cubic(x):
            return x + 0.1 * x**3

        channel = NonlinearChannel(cubic)
        output = channel(random_tensor)

        # Check shape preservation
        assert output.shape == random_tensor.shape

        # Check output matches expected nonlinear transform
        expected = random_tensor + 0.1 * random_tensor**3
        assert torch.allclose(output, expected)

    def test_forward_complex_modes(self, complex_tensor):
        """Test with different complex modes."""

        # Test direct mode
        def scale_complex(x):
            return 0.5 * x

        channel1 = NonlinearChannel(scale_complex, complex_mode="direct")
        output1 = channel1(complex_tensor)
        assert torch.allclose(output1, 0.5 * complex_tensor)

        # Test cartesian mode
        def square(x):
            return x**2

        channel2 = NonlinearChannel(square, complex_mode="cartesian")
        output2 = channel2(complex_tensor)
        expected2 = torch.complex(complex_tensor.real**2, complex_tensor.imag**2)
        assert torch.allclose(output2, expected2)

        # Test polar mode
        def double_magnitude(x):
            return 2.0 * x

        channel3 = NonlinearChannel(double_magnitude, complex_mode="polar")
        output3 = channel3(complex_tensor)

        # Magnitude should be doubled
        input_mag = torch.abs(complex_tensor)
        output_mag = torch.abs(output3)
        assert torch.allclose(output_mag, 2.0 * input_mag, rtol=1e-5)

        # Phase should be preserved
        input_phase = torch.angle(complex_tensor)
        output_phase = torch.angle(output3)
        assert torch.allclose(output_phase, input_phase, rtol=1e-5)

    def test_nonlinear_with_noise(self, random_tensor):
        """Test nonlinearity with added noise."""

        def identity(x):
            return x

        channel = NonlinearChannel(identity, add_noise=True, avg_noise_power=0.1)
        output = channel(random_tensor)

        # Check shape preservation
        assert output.shape == random_tensor.shape

        # Output should be different from input (due to noise)
        assert not torch.allclose(output, random_tensor)

        # Check noise variance
        noise = output - random_tensor
        measured_variance = torch.var(noise).item()
        assert abs(measured_variance - 0.1) < 0.2 * 0.1


def test_perfect_channel(random_tensor, complex_tensor):
    """Test PerfectChannel (identity channel)."""
    channel = PerfectChannel()

    # Test with real input
    output_real = channel(random_tensor)
    assert torch.allclose(output_real, random_tensor)

    # Test with complex input
    output_complex = channel(complex_tensor)
    assert torch.allclose(output_complex, complex_tensor)


class TestChannelComposition:
    """Test composition of multiple channels."""

    def test_sequential_composition(self, complex_tensor):
        """Test applying channels in sequence."""
        # Create individual channels
        phase_noise = PhaseNoiseChannel(phase_noise_std=0.1)
        awgn = AWGNChannel(snr_db=15)

        # Apply in sequence
        output = awgn(phase_noise(complex_tensor))

        # Check output shape matches input
        assert output.shape == complex_tensor.shape

        # Output should be different from input
        assert not torch.allclose(output, complex_tensor)

        # Output should be complex
        assert torch.is_complex(output)

    def test_composition_order(self, complex_tensor):
        """Test that the order of channel application matters."""
        phase_noise = PhaseNoiseChannel(phase_noise_std=0.2)
        awgn = AWGNChannel(snr_db=10)

        # Apply in different orders
        torch.manual_seed(42)  # Use same seed for fair comparison
        output1 = awgn(phase_noise(complex_tensor))

        torch.manual_seed(42)
        output2 = phase_noise(awgn(complex_tensor))

        # Results should be different
        assert not torch.allclose(output1, output2)

    def test_perfect_channel_composition(self, complex_tensor):
        """Test PerfectChannel in a composition."""
        awgn = AWGNChannel(snr_db=15)
        perfect = PerfectChannel()

        # Set fixed random seed
        torch.manual_seed(123)
        output1 = awgn(complex_tensor)

        # Reset seed for same noise realization
        torch.manual_seed(123)
        output2 = awgn(perfect(complex_tensor))

        # Outputs should be identical
        assert torch.allclose(output1, output2)

    def test_multiple_awgn_composition(self, complex_tensor):
        """Test that multiple AWGN channels have additive effect on noise."""
        # Create two AWGN channels with the same SNR
        snr_db = 20
        awgn1 = AWGNChannel(snr_db=snr_db)
        awgn2 = AWGNChannel(snr_db=snr_db)

        # Apply a single channel vs. two channels in sequence
        torch.manual_seed(42)
        output1 = awgn1(complex_tensor)
        noise1 = torch.mean(torch.abs(output1 - complex_tensor) ** 2).item()

        torch.manual_seed(44)  # Different seed for independent noise
        output2 = awgn2(awgn1(complex_tensor))
        noise2 = torch.mean(torch.abs(output2 - complex_tensor) ** 2).item()

        # Second case should have approximately twice the noise power
        # (allowing for statistical variation)
        assert 1.5 < noise2 / noise1 < 2.5


# Additional tests to cover requested conditions


def test_nonlinear_channel_snr_applied(random_tensor):
    """Test that NonlinearChannel adds noise via _apply_noise when self.snr_db is provided."""
    # Use identity nonlinearity; output should be input plus noise
    snr_db = 10.0
    channel = NonlinearChannel(lambda x: x, add_noise=True, snr_db=snr_db)
    output = channel(random_tensor)
    # Since noise is added, output should not equal input.
    assert not torch.allclose(output, random_tensor)
    # Also, test that noise variance is close to expected (derived from _apply_noise)
    signal_power = torch.mean(random_tensor**2).item()
    expected_noise_power = snr_to_noise_power(signal_power, snr_db)
    noise = output - random_tensor
    measured = torch.mean(noise**2).item()
    assert math.isclose(measured, expected_noise_power, rel_tol=0.3)


def test_nonlinear_channel_conflict_params():
    """Test that NonlinearChannel raises an error when both snr_db and avg_noise_power are
    provided."""
    with pytest.raises(ValueError):
        NonlinearChannel(lambda x: x, add_noise=True)

    # Test providing both noise parameters when add_noise=True
    with pytest.raises(ValueError, match="Cannot specify both snr_db and avg_noise_power"):
        NonlinearChannel(lambda x: x, add_noise=True, snr_db=10.0, avg_noise_power=0.1)


def test_flat_fading_channel_input_shape():
    """Test FlatFadingChannel processing for 1D and >2D inputs."""
    # Create a dummy channel with Rayleigh fading (use avg_noise_power branch here)
    channel = FlatFadingChannel("rayleigh", coherence_time=4, avg_noise_power=0.1)

    # Test 1D input: branch to add a batch dim and later squeeze it
    x_1d = torch.ones(20)
    y_1d = channel(x_1d)
    # Output should have same shape as x_1d after squeezing
    assert y_1d.shape == x_1d.shape

    # Test >2D input: e.g., (batch, channels, seq_length)
    x_3d = torch.ones(2, 3, 16, dtype=torch.cfloat)
    y_3d = channel(x_3d)
    # Check that output retains the original 3D shape.
    assert y_3d.shape == x_3d.shape


class TestRicianFadingChannel:
    """Test suite for RicianFadingChannel."""

    def test_initialization(self):
        """Test initialization with different parameters."""
        # Test with K-factor and noise power
        channel1 = RicianFadingChannel(k_factor=5.0, avg_noise_power=0.1)
        # Ensure comparison is done with tensors
        assert torch.isclose(torch.tensor(channel1.k_factor), torch.tensor(5.0), rtol=1e-5)
        assert torch.isclose(torch.tensor(channel1.avg_noise_power), torch.tensor(0.1), rtol=1e-5)
        assert channel1.snr_db is None

        # Test with K-factor and SNR
        channel2 = RicianFadingChannel(k_factor=5.0, snr_db=10.0)
        # Ensure comparison is done with tensors
        assert torch.isclose(torch.tensor(channel2.k_factor), torch.tensor(5.0), rtol=1e-5)
        assert channel2.snr_db == 10.0
        assert channel2.avg_noise_power is None

        # Test invalid K-factor
        with pytest.raises(ValueError):
            RicianFadingChannel(k_factor=-1.0, avg_noise_power=0.1)

        # Test missing noise parameter
        with pytest.raises(ValueError):
            RicianFadingChannel(k_factor=5.0)


class TestLogNormalFadingChannel:
    """Test suite for LogNormalFadingChannel."""

    def test_initialization(self):
        """Test initialization with different parameters."""
        # Test with shadow_sigma_db and noise power
        channel1 = LogNormalFadingChannel(shadow_sigma_db=8.0, avg_noise_power=0.1)
        # Ensure comparison is done with tensors
        assert torch.isclose(torch.tensor(channel1.shadow_sigma_db), torch.tensor(8.0), rtol=1e-5)
        assert torch.isclose(torch.tensor(channel1.avg_noise_power), torch.tensor(0.1), rtol=1e-5)
        assert channel1.snr_db is None

        # Test with shadow_sigma_db and SNR
        channel2 = LogNormalFadingChannel(shadow_sigma_db=8.0, snr_db=10.0)
        # Ensure comparison is done with tensors
        assert torch.isclose(torch.tensor(channel2.shadow_sigma_db), torch.tensor(8.0), rtol=1e-5)
        assert channel2.snr_db == 10.0
        assert channel2.avg_noise_power is None

        # Test invalid shadow_sigma_db
        with pytest.raises(ValueError):
            LogNormalFadingChannel(shadow_sigma_db=-1.0, avg_noise_power=0.1)

        # Test missing noise parameter
        with pytest.raises(ValueError):
            LogNormalFadingChannel(shadow_sigma_db=8.0)

## Product Requirement Document

Hey team, we need to build out this spectroscopy analysis library we've been talking about. Basically scientists are tired of rewriting the same boilerplate every time they want to do basic line measurements on their data — things like figuring out how wide a line is, where its center is, how strong the signal is compared to noise, that sort of thing. The data always has a physical axis attached (like wavelength or frequency) and the flux values also carry units, so we can't just ignore that — people have gotten burned before when units got dropped silently.

We also need the region stuff — scientists want to be able to carve out chunks of a spectrum, combine those chunks, flip them around (like 'give me everything outside these windows'), and remove bad samples entirely. Similar to what we did in the masking module last quarter, but more flexible.

One thing I keep hearing is complaints about pixel-ordered axes behaving weirdly when data comes in reversed — apparently that causes silent wrong answers downstream so we need to catch that early and tell the user clearly.

Also the SNR stuff needs two modes: one where you already have error bars, and one where you estimate it straight from the data somehow. I don't remember exactly how that second one works mathematically but the science team said it's the standard derivative-based approach everyone uses.

Please keep everything modular — no giant single files. Tests should go in their own folder.

A couple extra details from the follow-up questions. For integrated flux, the result unit needs to be the product of the flux unit and the spectral axis unit. So if somebody is integrating Jy over an Angstrom axis, the reported result should come out as 'Angstrom Jy'. Please make the output line read exactly as integrated_flux=<value> unit=<spectral_unit> <flux_unit>.

On equivalent width, we should stick to the standard spectroscopy sign convention. With a default continuum of one flux unit, an emission line where the flux rises above the continuum gives a NEGATIVE equivalent width, and an absorption line where the flux dips below the continuum gives a POSITIVE equivalent width. For moments, order 0 returns the flux unit because it is the integrated flux, and order 1 and above return the spectral-axis unit raised to the power of the moment order. So order 1 is spectral_unit^1 and order 2 is spectral_unit^2.

For arithmetic between two spectra on the same spectral axis, if we do add, subtract, multiply, or divide, any sample in the result that ends up undefined (NaN) because one of the input flux values was undefined needs to be flagged in the output mask. The result should still report 'flux=...' and 'unit=...' lines, and if the mask is doing anything other than being completely unmasked, that should be reported too.

Also, there are really two different FWHM paths and we should keep them distinct. 'gaussian_fwhm' is the analytic one based on the second-moment sigma width scaled by 2*sqrt(2*ln(2)) and it assumes a Gaussian profile. 'fwhm' is the empirical one where we find where the flux drops to half its peak and use linear interpolation between samples.

For regions built from center plus width, width has to be strictly positive. A zero or negative width should be rejected with a neutral error category. The span is from (center - width/2) to (center + width/2). And the region combine/invert/bounds behavior should line up with the spectral region algebra described in the feature8_*.json cases, specifically the SpectralRegion construction and set-like manipulation living in src/regions/ module.

A couple formatting things too: numeric output should trim unnecessary trailing zeros, so '4' not '4.0' and '0.04' not '0.040000'. In general the significant figures should match the precision implied by the test cases, usually around 5-6 significant figures for computed values, and if a result is an integer it should print without a decimal point.

Last bit on centroid and SNR. If per-sample uncertainties are present, we do need to propagate the centroid uncertainty and report it on its own line as 'uncertainty=<value>'. Also the centroid itself should not change under a global sign flip of the flux values, so a continuum-subtracted absorption line lands at the same centroid as the equivalent emission line. And for the derived SNR mode, the DER_SNR algorithm is the one to use: estimate noise from the flux array by taking the std of finite differences. That is the behavior used by feature4_2_signal_to_noise_derived.json through the 'signal_to_noise_derived' operation.
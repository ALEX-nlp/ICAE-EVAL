## Product Requirement Document

Hey team, we need to build out this spectroscopy analysis library we've been talking about. Basically scientists are tired of rewriting the same boilerplate every time they want to do basic line measurements on their data — things like figuring out how wide a line is, where its center is, how strong the signal is compared to noise, that sort of thing. The data always has a physical axis attached (like wavelength or frequency) and the flux values also carry units, so we can't just ignore that — people have gotten burned before when units got dropped silently.

We also need the region stuff — scientists want to be able to carve out chunks of a spectrum, combine those chunks, flip them around (like 'give me everything outside these windows'), and remove bad samples entirely. Similar to what we did in the masking module last quarter, but more flexible.

One thing I keep hearing is complaints about pixel-ordered axes behaving weirdly when data comes in reversed — apparently that causes silent wrong answers downstream so we need to catch that early and tell the user clearly.

Also the SNR stuff needs two modes: one where you already have error bars, and one where you estimate it straight from the data somehow. I don't remember exactly how that second one works mathematically but the science team said it's the standard derivative-based approach everyone uses.

Please keep everything modular — no giant single files. Tests should go in their own folder.